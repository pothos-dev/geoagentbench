"""Per-session Docker container lifecycle.

Thin wrapper around the ``docker`` CLI (no Python SDK dependency). The
harness uses these helpers to spawn one throwaway sandbox container per
agent session, exec tool calls inside it, shuttle files in/out via
``docker cp``, and tear it down when the session ends.

The container's workdir (``/work``) lives entirely in its writable
layer — we deliberately do NOT bind-mount a host directory. That keeps
us working when the harness itself runs inside a sibling Docker
container (e.g. with ``/var/run/docker.sock`` mounted): bind-mount
paths the harness sees aren't paths the daemon sees, so a bind mount
would silently mount an empty fresh dir on the sandbox. ``docker cp``
streams via the docker API (client reads the bytes, daemon writes them
into the container), so it works regardless of where the harness lives.

All subprocess calls use explicit argv lists (never ``shell=True``).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Default image tag. Override per call or globally via env.
SANDBOX_IMAGE = os.environ.get("GEOAGENTBENCH_SANDBOX_IMAGE", "geoagentbench-sandbox:latest")

_NAME_PREFIX = "geoagentbench-session-"
_LABEL_KEY = "geoagentbench.session"

# Docker container names: [a-zA-Z0-9][a-zA-Z0-9_.-]*. We strip everything
# else and collapse runs of separators so a label like "openrouter-gemma4
# -26b-detailed__crs-l1-paris" becomes a clean slug.
_SLUG_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_MAX_LABEL_LEN = 60


def _slugify(label: str) -> str:
    s = _SLUG_RE.sub("-", label).strip("-_.")
    return s[:_MAX_LABEL_LEN] if len(s) > _MAX_LABEL_LEN else s


def _name_for(session_id: str, label: str | None = None) -> str:
    """Container name. With *label*, returns
    ``geoagentbench-session-<slug>-<sid8>`` so post-mortem ``docker ps`` shows
    which adapter+task the container belongs to; ``<sid8>`` keeps reruns
    of the same (adapter, task) from clashing."""
    if label:
        slug = _slugify(label)
        if slug:
            return f"{_NAME_PREFIX}{slug}-{session_id[:8]}"
    return f"{_NAME_PREFIX}{session_id}"


def _container_exists(container_id: str) -> bool:
    """Return True iff ``docker inspect`` finds the container."""
    res = subprocess.run(
        ["docker", "inspect", "--format", "{{.Id}}", container_id],
        capture_output=True,
        text=True,
    )
    return res.returncode == 0


def start_session_container(
    *,
    session_id: str,
    image: str | None = None,
    label: str | None = None,
) -> str:
    """Spawn a detached sandbox container with no host bind mount.

    The container is named ``geoagentbench-session-<session_id>`` and labelled
    ``geoagentbench.session=<session_id>`` for easy filtering / debugging.
    Its workdir is ``/work`` (provided by ``WORKDIR /work`` in the
    sandbox Dockerfile) and lives in the container's writable layer —
    use :func:`copy_into` / :func:`copy_from` to move files across the
    boundary at session start/end.

    We deliberately do NOT pass ``--rm`` — ``stop_session_container``
    handles cleanup so failed sessions can be inspected post-mortem.

    Returns the full container ID.
    """
    img = image or SANDBOX_IMAGE
    name = _name_for(session_id, label)

    argv = [
        "docker", "run",
        "-d",
        "--name", name,
        "--label", f"{_LABEL_KEY}={session_id}",
        "--workdir", "/work",
        img,
    ]
    log.info("starting session container session_id=%s image=%s", session_id, img)
    res = subprocess.run(argv, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"docker run failed (exit {res.returncode}): {res.stderr.strip()}"
        )
    container_id = res.stdout.strip()
    log.info("started session container session_id=%s container_id=%s",
             session_id, container_id[:12])
    return container_id


def copy_into(
    container_id: str,
    host_path: Path,
    container_path: str = "/work",
) -> None:
    """Copy *host_path* (file or dir) into the container at *container_path*.

    Streams bytes via ``docker cp`` (which uses the docker API, not a
    bind mount), so it works correctly even when the harness runs
    inside a sibling container.

    ``docker cp`` has quirky trailing-slash / "create vs merge"
    semantics for directories — to avoid ambiguity, when *host_path* is
    a directory we always pass ``<host_path>/.`` so the *contents* are
    copied into *container_path* (which must already exist). When
    *host_path* is a file, it is copied to *container_path* (which may
    name the destination file or an existing destination directory).

    Raises ``RuntimeError`` if the container is gone or the copy fails.
    """
    if not _container_exists(container_id):
        raise RuntimeError(f"container {container_id!r} does not exist")

    src = Path(host_path)
    if src.is_dir():
        src_arg = f"{src.resolve()}/."
    else:
        src_arg = str(src.resolve())

    argv = ["docker", "cp", src_arg, f"{container_id}:{container_path}"]
    res = subprocess.run(argv, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"docker cp into container failed (exit {res.returncode}): "
            f"{res.stderr.strip()}"
        )


def copy_from(
    container_id: str,
    container_path: str,
    host_path: Path,
) -> None:
    """Copy *container_path* (file or dir) out of the container to *host_path*.

    Streams bytes via ``docker cp`` (which uses the docker API, not a
    bind mount), so it works correctly even when the harness runs
    inside a sibling container.

    ``docker cp`` has quirky trailing-slash / "create vs merge"
    semantics for directories. When *container_path* names a directory
    we always pass ``<container_path>/.`` so the *contents* are copied
    into *host_path* (which is created if missing). When
    *container_path* names a file, it is copied to *host_path*.

    Raises ``RuntimeError`` if the container is gone or the copy fails.
    """
    if not _container_exists(container_id):
        raise RuntimeError(f"container {container_id!r} does not exist")

    # Probe whether the source is a directory inside the container so we
    # can apply the `<src>/.` form consistently with copy_into.
    probe = subprocess.run(
        ["docker", "exec", container_id, "test", "-d", container_path],
        capture_output=True,
        text=True,
    )
    is_dir = probe.returncode == 0

    dst = Path(host_path)
    if is_dir:
        dst.mkdir(parents=True, exist_ok=True)
        src_arg = f"{container_id}:{container_path}/."
        dst_arg = str(dst.resolve())
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_arg = f"{container_id}:{container_path}"
        dst_arg = str(dst.resolve())

    argv = ["docker", "cp", src_arg, dst_arg]
    res = subprocess.run(argv, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"docker cp from container failed (exit {res.returncode}): "
            f"{res.stderr.strip()}"
        )


def exec_in(
    container_id: str,
    argv: list[str],
    *,
    timeout_s: int = 600,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run *argv* inside the container via ``docker exec``.

    *stdin*, if given, is piped to the process. *env* entries become
    ``-e KEY=VALUE`` flags. Raises ``RuntimeError`` if the container no
    longer exists. Propagates ``subprocess.TimeoutExpired`` on timeout.

    Stdout/stderr are captured as bytes and decoded as UTF-8 with
    ``errors='replace'`` so that ``Bash`` commands which print binary
    bytes (e.g. ``head`` over a parquet file) cannot crash the harness
    with ``UnicodeDecodeError``. Returned ``CompletedProcess`` carries
    ``str`` stdout/stderr for downstream code that expects text.
    """
    if not _container_exists(container_id):
        raise RuntimeError(f"container {container_id!r} does not exist")

    cmd: list[str] = ["docker", "exec"]
    if stdin is not None:
        cmd.append("-i")
    for k, v in (env or {}).items():
        cmd.extend(["-e", f"{k}={v}"])
    cmd.append(container_id)
    cmd.extend(argv)

    stdin_bytes = stdin.encode("utf-8") if stdin is not None else None
    res = subprocess.run(
        cmd,
        input=stdin_bytes,
        capture_output=True,
        timeout=timeout_s,
    )
    stdout = res.stdout.decode("utf-8", errors="replace") if res.stdout else ""
    stderr = res.stderr.decode("utf-8", errors="replace") if res.stderr else ""
    return subprocess.CompletedProcess(
        args=res.args, returncode=res.returncode, stdout=stdout, stderr=stderr
    )


def stop_session_container(container_id: str, *, remove: bool = True) -> None:
    """``docker stop`` (5s grace) then optionally ``docker rm``. Idempotent.

    Safe to call on a missing container — returns without error.
    """
    if not _container_exists(container_id):
        log.debug("stop: container %s already gone", container_id[:12])
        return

    stop_res = subprocess.run(
        ["docker", "stop", "-t", "5", container_id],
        capture_output=True,
        text=True,
    )
    if stop_res.returncode != 0:
        log.warning("docker stop failed for %s: %s",
                    container_id[:12], stop_res.stderr.strip())

    if remove:
        rm_res = subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            text=True,
        )
        if rm_res.returncode != 0:
            log.warning("docker rm failed for %s: %s",
                        container_id[:12], rm_res.stderr.strip())
        else:
            log.info("removed session container %s", container_id[:12])
