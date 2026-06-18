"""In-memory session state and the run-fn protocol."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from adapter_core.schemas import Event, EventType, SessionStatusName, UsageBlock

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class ContainerBackend(Protocol):
    """Lifecycle + file-shuttle calls the session store needs from the
    sandbox layer. Production wires this to :mod:`adapter_core.container`;
    tests can inject a lightweight stub so they don't need a docker daemon.
    """

    def start(self, session_id: str, label: str | None = None) -> str:
        """Spawn a sandbox container. Returns the container id. Raises on failure.

        *label* is a free-form hint (e.g. ``<adapter>__<task_id>``) that the
        backend uses to build a human-readable container name. Naming only —
        not used for routing or isolation.
        """

    def stop(self, container_id: str) -> None:
        """Tear down the container. Idempotent on missing container."""

    def copy_into(self, container_id: str, host_path: Path, container_path: str) -> None:
        """Push host files into the container."""

    def copy_from(self, container_id: str, container_path: str, host_path: Path) -> None:
        """Stream container files back to the host."""


class _DockerBackend:
    """Default backend wired to :mod:`adapter_core.container`.

    Imports lazily so unit tests that supply their own backend don't pull
    docker into the import graph.
    """

    def start(self, session_id: str, label: str | None = None) -> str:
        from adapter_core.container import start_session_container

        return start_session_container(session_id=session_id, label=label)

    def stop(self, container_id: str) -> None:
        from adapter_core.container import stop_session_container

        stop_session_container(container_id)

    def copy_into(self, container_id: str, host_path: Path, container_path: str) -> None:
        from adapter_core.container import copy_into

        copy_into(container_id, host_path, container_path)

    def copy_from(self, container_id: str, container_path: str, host_path: Path) -> None:
        from adapter_core.container import copy_from

        copy_from(container_id, container_path, host_path)


_DEFAULT_BACKEND = _DockerBackend()


RunFn = Callable[["Session", str], Awaitable[None]]
"""Adapter-specific async function. Reads `instruction` (already in the
event log as a synthesized user-turn event), drives the underlying agent,
appends events via session.append_event(), and updates usage via
session.set_usage_*(). Raises on failure — the core marks the session
`failed` with the exception's message. Cancellation arrives as
asyncio.CancelledError; the run_fn must propagate it."""


class Session:
    """One isolated agent session. State lives entirely in memory; files
    live under a flat directory the agent uses as its CWD."""

    def __init__(self, session_id: str, work_dir: Path) -> None:
        self.session_id = session_id
        self.work_dir = work_dir
        self.created_at = _now_iso()
        self.last_activity_at = self.created_at

        self.status: SessionStatusName = "idle"
        self.error: str | None = None
        self.events: list[Event] = []
        self.usage = UsageBlock()

        # Optional per-session model override supplied via X-Harness-Model
        # at session creation. Adapters consult this and fall back to their
        # own default when None.
        self.model_override: str | None = None

        # Optional per-session system-prompt variant supplied via
        # X-Harness-Prompt-Variant. Resolved against adapter_core.prompts;
        # None means "use process default".
        self.prompt_variant: str | None = None

        # Free-form bag for adapter-specific in-memory state (e.g., the
        # OpenRouter adapter's "files read so far" set used to enforce the
        # Read-before-Edit guard). Keys are namespaced by adapter.
        self.adapter_state: dict[str, object] = {}

        # Per-session sandbox container ID. Populated by ``SessionStore.create``
        # before the session is registered. Always set on a live session;
        # ``None`` only on a session whose container spawn failed (in which
        # case ``create`` has already raised and the session never reached
        # the store).
        self.container_id: str | None = None

        # True after the first message has been accepted. Adapters may
        # consult this but the contract no longer rejects follow-up messages
        # — a second POST /messages to an idle session is allowed (used by
        # the eval runner's nudge-on-missing-output logic).
        self.message_received = False

        # Active task for cancellation on DELETE.
        self._task: asyncio.Task[None] | None = None
        # Tracks running-interval start so duration_s sums correctly.
        self._running_started: float | None = None
        # Lock around state transitions so concurrent requests don't race.
        self.lock = asyncio.Lock()

    # ----- mutation helpers used by the core and by run_fn ----------------

    def append_event(
        self,
        type: EventType,
        content: Any,
        role: str | None = None,
    ) -> None:
        self.events.append(
            Event(ts=_now_iso(), type=type, role=role, content=content)  # type: ignore[arg-type]
        )
        self.last_activity_at = _now_iso()

    def set_model(self, model: str) -> None:
        self.usage.model = model

    def set_agent_version(self, version: str) -> None:
        self.usage.agent_version = version

    def add_cost(self, usd: float) -> None:
        self.usage.estimated_cost_usd += usd

    def _start_running(self) -> None:
        self.status = "running"
        self._running_started = time.monotonic()
        self.last_activity_at = _now_iso()

    def _stop_running(self) -> None:
        if self._running_started is not None:
            self.usage.duration_s += time.monotonic() - self._running_started
            self._running_started = None

    def _mark_idle(self) -> None:
        self._stop_running()
        self.status = "idle"
        self.last_activity_at = _now_iso()

    def _mark_failed(self, error: str) -> None:
        self._stop_running()
        self.status = "failed"
        self.error = error
        self.last_activity_at = _now_iso()


class SessionStore:
    """Process-local registry of live sessions.

    The sandbox-container backend is injected via *container_backend* so
    tests can drive the store without a real docker daemon. Production
    leaves it ``None`` and gets the default docker-CLI wiring.
    """

    def __init__(
        self,
        sessions_root: Path,
        max_concurrent: int,
        adapter_version: str,
        *,
        container_backend: ContainerBackend | None = None,
    ) -> None:
        self.sessions_root = sessions_root
        self.max_concurrent = max_concurrent
        self.adapter_version = adapter_version
        self._backend: ContainerBackend = container_backend or _DEFAULT_BACKEND
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self.sessions_root.mkdir(parents=True, exist_ok=True)

    def _running_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "running")

    async def create(self, label: str | None = None) -> Session | None:
        """Create a new session. Returns None if at concurrency limit.

        Each session gets its own sandbox container, spawned via
        ``adapter_core.container.start_session_container`` before the
        session is registered with the store. The on-disk ``work_dir``
        remains the host-side staging area: uploaded files land there,
        the container's ``/work`` is hydrated via ``copy_into`` before
        each run, and the container's final state is streamed back via
        ``copy_from`` after each run so the files endpoint keeps working.

        If the container fails to start the work_dir is rolled back and
        the exception is re-raised — no half-initialised session is left
        in the store.
        """
        async with self._lock:
            if self._running_count() >= self.max_concurrent:
                return None
            session_id = uuid.uuid4().hex
            work_dir = self.sessions_root / session_id
            work_dir.mkdir(parents=True, exist_ok=False)
            session = Session(session_id, work_dir)
            session.set_agent_version(self.adapter_version)

            try:
                session.container_id = self._backend.start(session_id, label=label)
            except Exception:
                log.exception(
                    "failed to start sandbox container for session %s",
                    session_id,
                )
                shutil.rmtree(work_dir, ignore_errors=True)
                raise

            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def delete(self, session_id: str) -> bool:
        """Cancel any in-flight task and remove the session from disk + memory.
        Returns False if the session was unknown."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False

        task = session._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass

        # Tear down the sandbox container. Best-effort: any failure here is
        # logged but does not block session removal.
        if session.container_id is not None:
            try:
                self._backend.stop(session.container_id)
            except Exception:
                log.exception(
                    "failed to stop sandbox container for session %s",
                    session_id,
                )

        # Best-effort cleanup of the on-disk pool.
        if session.work_dir.exists():
            shutil.rmtree(session.work_dir, ignore_errors=True)
        return True

    async def run_message(self, session: Session, instruction: str, run_fn: RunFn) -> None:
        """Drive the run_fn on a background task with proper state transitions.

        Transitions to ``running`` synchronously before the task is scheduled,
        so a poll between POST /messages returning 202 and the task actually
        starting cannot observe the post-completion idle state.

        Files currently staged under ``session.work_dir`` (e.g. uploaded
        via POST /files) are pushed into ``/work`` inside the container
        *before* ``run_fn`` runs. After ``run_fn`` returns — success,
        error, or cancellation — the container's ``/work`` contents are
        streamed back out to ``session.work_dir`` so the files endpoint
        and grader see the agent's final state.
        """
        session._start_running()

        # Hydrate the container's workdir from anything currently staged on
        # the host (uploaded inputs). Done off the background task so that
        # any docker error surfaces synchronously and turns into a failed
        # session rather than a silent missing-input.
        if session.container_id is not None:
            try:
                # Only copy if there's actually something to push; an empty
                # work_dir is a legitimate "no inputs" case.
                if any(session.work_dir.iterdir()):
                    self._backend.copy_into(
                        session.container_id, session.work_dir, "/work"
                    )
            except Exception as exc:
                session._mark_failed(
                    f"container input staging failed: {type(exc).__name__}: {exc}"
                )
                return

        backend = self._backend

        async def _wrapped() -> None:
            try:
                await run_fn(session, instruction)
                session._mark_idle()
            except asyncio.CancelledError:
                session._mark_failed("cancelled")
                raise
            except Exception as exc:  # noqa: BLE001 — surface anything as failed
                session._mark_failed(f"{type(exc).__name__}: {exc}")
            finally:
                # Sync the container's workdir back to disk on every exit
                # path so the files endpoint / grader can read final state.
                if session.container_id is not None:
                    try:
                        backend.copy_from(
                            session.container_id, "/work/.", session.work_dir
                        )
                    except Exception:
                        log.exception(
                            "copy_from /work failed for session %s",
                            session.session_id,
                        )

        session._task = asyncio.create_task(_wrapped())
