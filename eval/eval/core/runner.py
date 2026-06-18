"""Runner: drive one or more tasks through an adapter's session lifecycle.

See eval-app-design.md "Run lifecycle". One run = one (adapter, task-filter)
combination; this module knows nothing about CLI vs. UI invocation.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from eval.core.scoring import score_task
from eval.core.storage import RunStore, new_run_id, utc_iso
from eval.core.tasks import Task, load_tasks, filter_tasks

POLL_INTERVAL = 2.0
TRANSCRIPT_FETCH_INTERVAL = 5.0  # seconds between live transcript fetches
HTTP_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
# If the session's last_activity_at hasn't changed for this long, consider it
# stalled and kill it. Protects against hung processes (e.g. `tail -f`).
STALL_TIMEOUT = float(os.environ.get("HARNESS_STALL_TIMEOUT", "600"))  # 10 min


def is_max_iterations_error(error: str | None) -> bool:
    """True if a session failure is the model running out of steps.

    This is the one *acceptable* failure — it reflects the model failing to
    finish the task, not infrastructure. We track it separately so reruns can
    skip these while still retrying infra failures (timeouts, connection
    drops, bad provider responses).
    """
    return bool(error) and "max iterations" in str(error).lower()


def is_rerunnable(task_state: dict) -> bool:
    """Whether a task should be (re-)run by resume.

    Anything not yet done is rerunnable, EXCEPT a genuine max-iterations model
    failure (flagged via ``max_iterations_reached``), which stays failed.
    """
    if task_state.get("max_iterations_reached"):
        return False
    return task_state.get("status") in ("pending", "running", "failed", "cancelled")


# Sidecar extensions that ship alongside a .shp in the ESRI Shapefile
# multi-file format. .shp + .shx + .dbf is the minimum for a complete
# read; .prj carries the CRS, .cpg the codepage. Without these the agent
# only sees raw geometry and (correctly) gives up.
_SHAPEFILE_SIDECARS = (".shx", ".dbf", ".prj", ".cpg")


def _expand_inputs(inp, primary: "Path") -> "list[Path]":
    """Return the actual files to upload for one declared input.

    Shapefiles are logically one input but physically several files;
    task.json only names the .shp, so we walk siblings here. Other
    formats just pass through."""
    fmt = (inp.format or "").lower()
    if fmt != "shapefile":
        return [primary]
    out = [primary]
    for ext in _SHAPEFILE_SIDECARS:
        sibling = primary.with_suffix(ext)
        if sibling.is_file():
            out.append(sibling)
    return out


@dataclass
class AdapterTarget:
    url: str
    name: str | None = None  # null for ad-hoc --agent-url
    label: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    max_concurrent_sessions: int | None = None
    attributes: dict = field(default_factory=dict)


@dataclass
class RunSpec:
    adapter: AdapterTarget
    task_filter: list[str] | None = None
    max_parallel: int | None = None  # CLI override; falls back to adapter's
    label: str | None = None


def _env_substitute(s: str) -> str:
    """Replace ${VAR} occurrences with os.environ values; missing → empty."""
    return re.sub(r"\$\{([A-Z0-9_]+)\}", lambda m: os.environ.get(m.group(1), ""), s)


def _resolve_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: _env_substitute(v) for k, v in headers.items()}


def _git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).resolve().parent,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        return None
    return None


def _initial_state(run_id: str, spec: RunSpec, tasks: list[Task], max_parallel: int) -> dict:
    return {
        "run_id": run_id,
        "schema_version": 1,
        "started_at": utc_iso(),
        "finished_at": None,
        "status": "running",
        "label": spec.label,
        "adapter": {
            "name": spec.adapter.name,
            "label": spec.adapter.label,
            "url": spec.adapter.url,
            "attributes": spec.adapter.attributes,
        },
        "invocation": {
            "max_parallel": max_parallel,
            "task_filter": spec.task_filter,
            "suite_git_sha": _git_sha(),
        },
        "tasks": {
            t.task_id: {
                "status": "pending",
                "session_id": None,
                "started_at": None,
                "finished_at": None,
                "duration_s": None,
                "estimated_cost_usd": None,
                "reported_model": None,
                "reported_agent_version": None,
                "score": None,
                "error": None,
                "last_event": "",
                # Snapshot the task content version at run start so the UI
                # can later flag the run as outdated when the task moves on.
                "task_version": t.version,
            }
            for t in tasks
        },
    }


async def _run_visualizer(task: Task, task_run_dir: Path) -> None:
    if not task.visualize_py.is_file():
        return
    from eval.core.viz import generate_layers

    generate_layers(
        task.visualize_py, task_run_dir / "outputs", task_run_dir / "visualizations"
    )


def _extract_last_activity(events: list[dict]) -> str:
    """Return a short label describing the model's latest activity.

    Walks the event list backwards and returns the first meaningful label,
    e.g. "Bash", "Write /out.gpkg", "Thinking".
    """
    for ev in reversed(events):
        etype = ev.get("type")
        if etype == "tool_call":
            content = ev.get("content") or {}
            name = content.get("name", "tool")
            args = content.get("arguments") or {}
            # Add a short hint for common tools
            if name == "Bash":
                cmd = args.get("command", "")
                first_line = cmd.split("\n", 1)[0][:60]
                return f"Bash: {first_line}" if first_line else "Bash"
            if name in ("Write", "Edit", "Read"):
                path = args.get("file_path", "")
                short = path.rsplit("/", 1)[-1] if "/" in path else path
                return f"{name} {short}" if short else name
            if name in ("Glob", "Grep"):
                pattern = args.get("pattern", "")
                return f"{name} {pattern[:40]}" if pattern else name
            return name
        if etype == "tool_result":
            continue  # skip results, look for the preceding call
        if etype == "thinking":
            return "Thinking"
        if etype == "text" and ev.get("role") == "assistant":
            return "Responding"
    return ""


async def _run_one_task(
    task: Task,
    spec: RunSpec,
    store: RunStore,
    client: httpx.AsyncClient,
) -> None:
    task_id = task.task_id
    task_run_dir = store.task_dir(task_id)
    outputs_dir = task_run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    def update(**fields):
        store.update_task(task_id, fields)

    started = asyncio.get_event_loop().time()
    update(status="running", started_at=utc_iso(), last_event="creating session")

    if store.is_cancelled():
        update(status="cancelled", finished_at=utc_iso(), last_event="cancelled before start")
        return

    session_id: str | None = None
    final_status_data: dict | None = None
    last_transcript_fetch = 0.0

    last_activity: str = ""

    async def _fetch_transcript_if_due(force: bool = False) -> None:
        """Fetch and save transcript periodically so the UI can show progress."""
        nonlocal last_transcript_fetch, last_activity
        now = asyncio.get_event_loop().time()
        if not force and (now - last_transcript_fetch) < TRANSCRIPT_FETCH_INTERVAL:
            return
        try:
            r = await client.get(f"/sessions/{session_id}/messages")
            if r.status_code == 200:
                payload = r.json()
                (task_run_dir / "transcript.json").write_text(
                    json.dumps(payload, indent=2) + "\n"
                )
                last_transcript_fetch = now
                last_activity = _extract_last_activity(payload.get("events", []))
        except Exception:
            pass  # non-critical — best-effort live view

    try:
        # POST /sessions — pass adapter+task as a label so the harness can
        # name the sandbox container something a human can read in
        # `docker ps` (e.g. lingering containers after a host reboot).
        adapter_name = spec.adapter.name or "adhoc"
        session_headers = {"X-Harness-Label": f"{adapter_name}__{task.task_id}"}
        r = await client.post("/sessions", headers=session_headers)
        r.raise_for_status()
        session_id = r.json()["session_id"]
        update(session_id=session_id, last_event=f"session {session_id}")

        # Upload inputs (plus shapefile sidecars when applicable)
        for inp in task.inputs:
            path = inp.path
            if not path.is_file():
                raise FileNotFoundError(f"input file not found: {path}")
            for fpath in _expand_inputs(inp, path):
                update(last_event=f"uploading {fpath.name}")
                with fpath.open("rb") as fh:
                    files = {"file": (fpath.name, fh, "application/octet-stream")}
                    rr = await client.post(
                        f"/sessions/{session_id}/files", files=files
                    )
                    rr.raise_for_status()

        # POST /sessions/{id}/messages
        update(last_event="posting instruction")
        r = await client.post(
            f"/sessions/{session_id}/messages",
            json={"instruction": task.instruction},
        )
        r.raise_for_status()

        # Poll
        prev_activity_at: str | None = None
        stall_since: float | None = None
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            if store.is_cancelled():
                update(last_event="cancellation requested")
                break
            r = await client.get(f"/sessions/{session_id}")
            r.raise_for_status()
            data = r.json()
            final_status_data = data
            usage = data.get("usage") or {}
            await _fetch_transcript_if_due()
            event_label = last_activity or f"status={data.get('status')}"
            update(
                last_event=event_label,
                estimated_cost_usd=usage.get("estimated_cost_usd"),
                reported_model=usage.get("model"),
                reported_agent_version=usage.get("agent_version"),
            )
            if data.get("status") in ("idle", "failed"):
                break
            # Stall detection: kill session if no activity for STALL_TIMEOUT
            activity_at = data.get("last_activity_at")
            if activity_at != prev_activity_at:
                prev_activity_at = activity_at
                stall_since = asyncio.get_event_loop().time()
            elif stall_since and (asyncio.get_event_loop().time() - stall_since) > STALL_TIMEOUT:
                update(last_event=f"stalled for {STALL_TIMEOUT:.0f}s — killing session")
                with suppress(Exception):
                    await client.delete(f"/sessions/{session_id}")
                raise RuntimeError(f"session stalled for {STALL_TIMEOUT:.0f}s (no activity since {activity_at})")

        if store.is_cancelled() and (
            final_status_data is None or final_status_data.get("status") == "running"
        ):
            update(status="cancelled", finished_at=utc_iso(), last_event="cancelled")
            return

        adapter_status = (final_status_data or {}).get("status")
        adapter_error = (final_status_data or {}).get("error")

        # Download files
        update(last_event="listing files")
        r = await client.get(f"/sessions/{session_id}/files")
        r.raise_for_status()
        listed = r.json().get("files", [])
        for fname in listed:
            update(last_event=f"downloading {fname}")
            r = await client.get(f"/sessions/{session_id}/files/{fname}")
            if r.status_code != 200:
                continue
            (outputs_dir / fname).write_bytes(r.content)

        # Get transcript
        update(last_event="fetching transcript")
        r = await client.get(f"/sessions/{session_id}/messages")
        r.raise_for_status()
        (task_run_dir / "transcript.json").write_text(
            json.dumps(r.json(), indent=2) + "\n"
        )

        # session.json — final status + file list. Stamp the task version
        # the run was scored against; runs predating this field are treated
        # as v0 (outdated) by the UI.
        (task_run_dir / "session.json").write_text(
            json.dumps(
                {
                    **(final_status_data or {}),
                    "files": listed,
                    "task_version": task.version,
                },
                indent=2,
            )
            + "\n"
        )

        if adapter_status == "failed":
            update(
                status="failed",
                error=adapter_error or "adapter reported failed",
                last_event=f"failed: {adapter_error}",
                max_iterations_reached=is_max_iterations_error(adapter_error),
                finished_at=utc_iso(),
                duration_s=round(asyncio.get_event_loop().time() - started, 2),
            )
            return

        # Score inline
        update(last_event="scoring")
        score = score_task(task, task_run_dir)
        update(score=score.get("score"))

        # Nudge: if the first gate failed with a missing output file, send
        # one follow-up message asking the model to finish, then re-grade.
        if (
            score.get("score") is not None
            and score["score"] == 0
            and any(
                not g["passed"] and "missing output file" in g.get("detail", "")
                for g in score.get("gates", [])
            )
        ):
            update(last_event="nudging — missing output file")
            nudge_msg = (
                "You are not done yet. The expected output file is missing. "
                "Please re-read the original instructions and finish the task."
            )
            r = await client.post(
                f"/sessions/{session_id}/messages",
                json={"instruction": nudge_msg},
            )
            if r.status_code == 202:
                nudge_prev_activity: str | None = None
                nudge_stall_since: float | None = None
                while True:
                    await asyncio.sleep(POLL_INTERVAL)
                    if store.is_cancelled():
                        break
                    r = await client.get(f"/sessions/{session_id}")
                    r.raise_for_status()
                    data = r.json()
                    final_status_data = data
                    usage = data.get("usage") or {}
                    await _fetch_transcript_if_due()
                    event_label = last_activity or f"nudge status={data.get('status')}"
                    update(
                        last_event=event_label,
                        estimated_cost_usd=usage.get("estimated_cost_usd"),
                    )
                    if data.get("status") in ("idle", "failed"):
                        break
                    activity_at = data.get("last_activity_at")
                    if activity_at != nudge_prev_activity:
                        nudge_prev_activity = activity_at
                        nudge_stall_since = asyncio.get_event_loop().time()
                    elif nudge_stall_since and (asyncio.get_event_loop().time() - nudge_stall_since) > STALL_TIMEOUT:
                        update(last_event=f"stalled for {STALL_TIMEOUT:.0f}s — killing session")
                        with suppress(Exception):
                            await client.delete(f"/sessions/{session_id}")
                        raise RuntimeError(f"nudge session stalled for {STALL_TIMEOUT:.0f}s")

                # Re-download files and re-grade
                update(last_event="re-downloading after nudge")
                r = await client.get(f"/sessions/{session_id}/files")
                r.raise_for_status()
                listed = r.json().get("files", [])
                for fname in listed:
                    r = await client.get(f"/sessions/{session_id}/files/{fname}")
                    if r.status_code == 200:
                        (outputs_dir / fname).write_bytes(r.content)

                # Re-fetch transcript
                r = await client.get(f"/sessions/{session_id}/messages")
                r.raise_for_status()
                (task_run_dir / "transcript.json").write_text(
                    json.dumps(r.json(), indent=2) + "\n"
                )

                update(last_event="re-scoring after nudge")
                score = score_task(task, task_run_dir)
                update(score=score.get("score"))

        # Visualise inline
        update(last_event="visualising")
        await _run_visualizer(task, task_run_dir)

        update(
            status="done",
            finished_at=utc_iso(),
            duration_s=round(asyncio.get_event_loop().time() - started, 2),
            last_event="done",
            max_iterations_reached=False,
        )

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        update(
            status="failed",
            error=err,
            last_event=f"error: {e}",
            max_iterations_reached=is_max_iterations_error(err),
            finished_at=utc_iso(),
            duration_s=round(asyncio.get_event_loop().time() - started, 2),
        )
    finally:
        if session_id is not None:
            with suppress(Exception):
                await client.delete(f"/sessions/{session_id}")


async def _run_async(spec: RunSpec, runs_root: Path) -> Path:
    tasks_all = load_tasks()
    tasks = filter_tasks(tasks_all, spec.task_filter)
    if not tasks:
        raise SystemExit("No tasks matched the filter.")

    max_parallel = (
        spec.max_parallel
        or spec.adapter.max_concurrent_sessions
        or 1
    )

    run_id = new_run_id()
    state = _initial_state(run_id, spec, tasks, max_parallel)
    store = RunStore.create(runs_root, run_id, state)

    sem = asyncio.Semaphore(max_parallel)
    headers = _resolve_headers(spec.adapter.headers)
    async with httpx.AsyncClient(
        base_url=spec.adapter.url, timeout=HTTP_TIMEOUT, headers=headers
    ) as client:

        async def _limited(t: Task) -> None:
            if store.is_cancelled():
                store.update_task(
                    t.task_id, {"status": "cancelled", "last_event": "cancelled before start"}
                )
                return
            async with sem:
                await _run_one_task(t, spec, store, client)

        await asyncio.gather(*[_limited(t) for t in tasks])

    if store.is_cancelled():
        store.set_status("cancelled", finished_at=utc_iso())
    else:
        any_failed = any(
            t.get("status") == "failed" for t in store.state.get("tasks", {}).values()
        )
        store.set_status("failed" if any_failed else "done", finished_at=utc_iso())

    return store.run_dir


async def _resume_async(run_dir: Path, max_parallel: int | None = None) -> Path:
    """Resume incomplete tasks in an existing run directory."""
    store = RunStore.open(run_dir)
    state = store.state

    # Remove stale cancel flag so the run can proceed
    if store.cancel_flag.exists():
        store.cancel_flag.unlink()

    # Identify tasks that need to be re-run. A max-iterations failure is a
    # genuine model failure, not infra, so it is left as-is rather than retried.
    task_ids_to_run = [
        tid for tid, t in state.get("tasks", {}).items()
        if is_rerunnable(t)
    ]
    if not task_ids_to_run:
        print("nothing to resume — all tasks already done")
        return run_dir

    # Reset those tasks to pending. Re-snapshot task_version against the
    # *current* task.json — resuming after a bump means the resumed attempt
    # is scored against the new version, so the recorded version must match.
    all_tasks_for_version = {t.task_id: t for t in load_tasks()}
    for tid in task_ids_to_run:
        t_def = all_tasks_for_version.get(tid)
        store.update_task(tid, {
            "status": "pending",
            "session_id": None,
            "started_at": None,
            "finished_at": None,
            "duration_s": None,
            "estimated_cost_usd": None,
            "reported_model": None,
            "reported_agent_version": None,
            "score": None,
            "error": None,
            "last_event": "pending (resumed)",
            "max_iterations_reached": False,
            "task_version": t_def.version if t_def else 1,
        })
    store.set_status("running", finished_at=None)

    # Reconstruct adapter target — prefer loading from adapters.yaml (has headers)
    adapter_info = state.get("adapter", {})
    adapter_name = adapter_info.get("name")
    adapter = None
    if adapter_name:
        from eval.core.adapters import load_adapters
        adapters = load_adapters()
        adapter = adapters.get(adapter_name)
    if adapter is None:
        adapter = AdapterTarget(
            url=adapter_info["url"],
            name=adapter_name,
            label=adapter_info.get("label"),
            attributes=adapter_info.get("attributes", {}),
        )

    # Load task definitions for the tasks we need to re-run
    all_tasks = {t.task_id: t for t in load_tasks()}
    tasks = [all_tasks[tid] for tid in task_ids_to_run if tid in all_tasks]
    if not tasks:
        raise SystemExit("No matching task definitions found for resumable tasks.")

    mp = (
        max_parallel
        or state.get("invocation", {}).get("max_parallel")
        or 1
    )

    sem = asyncio.Semaphore(mp)
    headers = _resolve_headers(adapter.headers)
    spec = RunSpec(adapter=adapter)

    async with httpx.AsyncClient(
        base_url=adapter.url, timeout=HTTP_TIMEOUT, headers=headers
    ) as client:

        async def _limited(t: Task) -> None:
            if store.is_cancelled():
                store.update_task(
                    t.task_id, {"status": "cancelled", "last_event": "cancelled before start"}
                )
                return
            async with sem:
                await _run_one_task(t, spec, store, client)

        await asyncio.gather(*[_limited(t) for t in tasks])

    if store.is_cancelled():
        store.set_status("cancelled", finished_at=utc_iso())
    else:
        any_failed = any(
            t.get("status") == "failed" for t in store.state.get("tasks", {}).values()
        )
        store.set_status("failed" if any_failed else "done", finished_at=utc_iso())

    return run_dir


async def _rerun_task_async(run_dir: Path, task_id: str) -> Path:
    """Wipe one task's artefacts and re-run it under its original run."""
    import shutil

    store = RunStore.open(run_dir)
    state = store.state

    task_state = state.get("tasks", {}).get(task_id)
    if task_state is None:
        raise SystemExit(f"task {task_id} not part of run")
    if task_state.get("status") in ("pending", "running"):
        raise SystemExit(f"task {task_id} is already {task_state['status']}")

    if store.cancel_flag.exists():
        store.cancel_flag.unlink()

    task_run_dir = run_dir / task_id
    for child in ("outputs", "visualizations"):
        p = task_run_dir / child
        if p.is_dir():
            shutil.rmtree(p)
    for child in ("transcript.json", "score.json", "session.json"):
        p = task_run_dir / child
        if p.is_file():
            p.unlink()

    all_tasks = {t.task_id: t for t in load_tasks()}
    task_def = all_tasks.get(task_id)
    if task_def is None:
        raise SystemExit(f"no task definition for {task_id}")

    store.update_task(task_id, {
        "status": "pending",
        "session_id": None,
        "started_at": None,
        "finished_at": None,
        "duration_s": None,
        "estimated_cost_usd": None,
        "reported_model": None,
        "reported_agent_version": None,
        "score": None,
        "error": None,
        "last_event": "pending (rerun)",
        "task_version": task_def.version,
    })
    store.set_status("running", finished_at=None)

    adapter_info = state.get("adapter", {})
    adapter_name = adapter_info.get("name")
    adapter = None
    if adapter_name:
        from eval.core.adapters import load_adapters
        adapter = load_adapters().get(adapter_name)
    if adapter is None:
        adapter = AdapterTarget(
            url=adapter_info["url"],
            name=adapter_name,
            label=adapter_info.get("label"),
            attributes=adapter_info.get("attributes", {}),
        )

    headers = _resolve_headers(adapter.headers)
    spec = RunSpec(adapter=adapter)
    async with httpx.AsyncClient(
        base_url=adapter.url, timeout=HTTP_TIMEOUT, headers=headers
    ) as client:
        await _run_one_task(task_def, spec, store, client)

    if store.is_cancelled():
        store.set_status("cancelled", finished_at=utc_iso())
    else:
        any_failed = any(
            t.get("status") == "failed" for t in store.state.get("tasks", {}).values()
        )
        store.set_status("failed" if any_failed else "done", finished_at=utc_iso())

    return run_dir


def run(spec: RunSpec, runs_root: Path) -> Path:
    """Sync entrypoint."""
    return asyncio.run(_run_async(spec, runs_root))


def resume(run_dir: Path, max_parallel: int | None = None) -> Path:
    """Sync entrypoint for resuming an interrupted run."""
    return asyncio.run(_resume_async(run_dir, max_parallel))


def rerun_task(run_dir: Path, task_id: str) -> Path:
    """Sync entrypoint for re-running a single task in an existing run."""
    return asyncio.run(_rerun_task_async(run_dir, task_id))
