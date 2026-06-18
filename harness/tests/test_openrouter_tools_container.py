"""Integration test for the OpenRouter tools running inside a sandbox container.

Spins a real container per test (no host bind mount; ``docker cp`` for
files), drives the tools through ``execute_tool``, and asserts the agent
can write -> read its own file. Skipped if Docker is unreachable or the
prebuilt sandbox image is missing — we never build from a test.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest

from adapter_core.container import (
    SANDBOX_IMAGE,
    start_session_container,
    stop_session_container,
)
from adapter_core.sessions import Session
from openrouter.tools import ToolError, execute_tool

# ----------------------------------------------------------------- skip gate

_DOCKER_SOCK = "/var/run/docker.sock"


def _docker_reachable() -> bool:
    if not os.path.exists(_DOCKER_SOCK):
        return False
    res = subprocess.run(
        ["docker", "version"], capture_output=True, text=True
    )
    return res.returncode == 0


def _image_available(tag: str) -> bool:
    res = subprocess.run(
        ["docker", "image", "inspect", tag], capture_output=True, text=True
    )
    return res.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_reachable() or not _image_available(SANDBOX_IMAGE),
    reason=(
        "docker daemon unreachable or sandbox image not built locally — "
        f"build with `docker build -t {SANDBOX_IMAGE} "
        "-f benchmark/harness/sandbox/Dockerfile benchmark/harness/sandbox/`"
    ),
)


# ----------------------------------------------------------------- fixture


@pytest.fixture
def container_session(tmp_path: Path):
    """A Session bound to a fresh sandbox container. Tears down at exit."""
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    s = Session(session_id=session_id, work_dir=tmp_path)
    s.container_id = cid
    try:
        yield s
    finally:
        stop_session_container(cid)


# ----------------------------------------------------------------- tests


async def test_write_then_read_roundtrip(container_session: Session) -> None:
    """Write a file via the Write tool, read it back via Read, content matches."""
    payload = "hello-from-container\nline-2\n"

    write_out = await execute_tool(
        container_session,
        "Write",
        {"file_path": "/work/hello.txt", "content": payload},
    )
    assert "Wrote" in write_out

    read_out = await execute_tool(
        container_session,
        "Read",
        {"file_path": "/work/hello.txt"},
    )
    # cat -n style: each source line gets prefixed with "%6d\t".
    assert "hello-from-container" in read_out
    assert "line-2" in read_out


async def test_bash_runs_inside_container(container_session: Session) -> None:
    """A Bash command should see the container's root fs, not the host's."""
    out = await execute_tool(
        container_session,
        "Bash",
        {"command": "id -u && pwd"},
    )
    assert "<exit_code>0</exit_code>" in out
    # WORKDIR in the sandbox Dockerfile is /work.
    assert "/work" in out


async def test_path_outside_workdir_rejected(container_session: Session) -> None:
    """Read of /etc/passwd must be refused by the workdir guard, regardless
    of whether the file exists inside the container."""
    with pytest.raises(ToolError, match="inside the working directory"):
        await execute_tool(
            container_session,
            "Read",
            {"file_path": "/etc/passwd"},
        )


async def test_relative_path_is_resolved_under_work(
    container_session: Session,
) -> None:
    """Relative file_path values should be joined onto /work."""
    await execute_tool(
        container_session,
        "Write",
        {"file_path": "rel.txt", "content": "x"},
    )
    out = await execute_tool(
        container_session,
        "Read",
        {"file_path": "rel.txt"},
    )
    assert "x" in out
