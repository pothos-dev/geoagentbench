"""Integration tests for adapter_core.container.

Exercises a real Docker daemon. The whole module is skipped if Docker is
unreachable. Individual tests that need the prebuilt sandbox image are
skipped if it isn't available locally (we never build from a test).

The sandbox container's workdir is in its writable layer (no host bind
mount), so these tests use ``copy_into`` / ``copy_from`` to shuttle
files across the boundary — which works regardless of whether the
runner is on the host or inside a sibling container.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest

from adapter_core.container import (
    SANDBOX_IMAGE,
    copy_from,
    copy_into,
    exec_in,
    start_session_container,
    stop_session_container,
)

# ----------------------------------------------------------------- skip gate

_DOCKER_SOCK = "/var/run/docker.sock"


def _docker_reachable() -> bool:
    if not os.path.exists(_DOCKER_SOCK):
        return False
    res = subprocess.run(
        ["docker", "version"], capture_output=True, text=True
    )
    return res.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_reachable(),
    reason="docker daemon not reachable (no /var/run/docker.sock or `docker version` failed)",
)


def _image_available(tag: str) -> bool:
    res = subprocess.run(
        ["docker", "image", "inspect", tag], capture_output=True, text=True
    )
    return res.returncode == 0


def _needs_image() -> None:
    if not _image_available(SANDBOX_IMAGE):
        pytest.skip(
            f"sandbox image {SANDBOX_IMAGE!r} not built locally — "
            f"run `docker build -t {SANDBOX_IMAGE} -f benchmark/harness/sandbox/Dockerfile benchmark/harness/sandbox/`"
        )


def _container_exists(cid: str) -> bool:
    res = subprocess.run(
        ["docker", "inspect", "--format", "{{.Id}}", cid],
        capture_output=True,
        text=True,
    )
    return res.returncode == 0


# ----------------------------------------------------------------- tests


def test_start_exec_stop_roundtrip() -> None:
    _needs_image()
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    try:
        res = exec_in(cid, ["echo", "hello"], timeout_s=10)
        assert res.returncode == 0
        assert res.stdout.strip() == "hello"
    finally:
        stop_session_container(cid)
    assert not _container_exists(cid), "container should be removed after stop"


def test_exec_timeout_raises() -> None:
    _needs_image()
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            exec_in(cid, ["sleep", "10"], timeout_s=1)
    finally:
        stop_session_container(cid)


def test_copy_into_then_exec_sees_file(tmp_path: Path) -> None:
    """Write a file on the host, copy it in, verify the agent can read it."""
    _needs_image()
    session_id = uuid.uuid4().hex

    src = tmp_path / "input.txt"
    src.write_text("host-wrote-this\n")

    cid = start_session_container(session_id=session_id)
    try:
        copy_into(cid, src, "/work")
        res = exec_in(cid, ["cat", "/work/input.txt"], timeout_s=10)
        assert res.returncode == 0, res.stderr
        assert res.stdout.strip() == "host-wrote-this"
    finally:
        stop_session_container(cid)


def test_copy_from_sees_container_writes(tmp_path: Path) -> None:
    """Agent writes a file in /work, copy_from streams it back to host."""
    _needs_image()
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    try:
        res = exec_in(
            cid,
            ["sh", "-c", "echo agent-wrote-this > /work/hello.txt"],
            timeout_s=10,
        )
        assert res.returncode == 0, res.stderr

        out_file = tmp_path / "hello.txt"
        copy_from(cid, "/work/hello.txt", out_file)
        assert out_file.exists()
        assert out_file.read_text().strip() == "agent-wrote-this"
    finally:
        stop_session_container(cid)


def test_copy_roundtrip_modify_inside(tmp_path: Path) -> None:
    """Full roundtrip: host->container->modify-inside->host sees change."""
    _needs_image()
    session_id = uuid.uuid4().hex

    src = tmp_path / "data.txt"
    src.write_text("v1")

    cid = start_session_container(session_id=session_id)
    try:
        copy_into(cid, src, "/work")

        res = exec_in(cid, ["cat", "/work/data.txt"], timeout_s=10)
        assert res.returncode == 0
        assert res.stdout == "v1"

        res = exec_in(
            cid,
            ["sh", "-c", "printf v2 > /work/data.txt"],
            timeout_s=10,
        )
        assert res.returncode == 0, res.stderr

        out = tmp_path / "out" / "data.txt"
        copy_from(cid, "/work/data.txt", out)
        assert out.read_text() == "v2"
    finally:
        stop_session_container(cid)


def test_copy_into_directory_contents(tmp_path: Path) -> None:
    """copy_into of a directory copies its contents into the destination."""
    _needs_image()
    session_id = uuid.uuid4().hex

    src_dir = tmp_path / "bundle"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("A")
    (src_dir / "b.txt").write_text("B")

    cid = start_session_container(session_id=session_id)
    try:
        copy_into(cid, src_dir, "/work")
        res = exec_in(cid, ["sh", "-c", "cat /work/a.txt /work/b.txt"], timeout_s=10)
        assert res.returncode == 0, res.stderr
        assert res.stdout == "AB"
    finally:
        stop_session_container(cid)


def test_container_cannot_see_arbitrary_host_paths() -> None:
    """No bind mount means host paths aren't reachable from inside."""
    _needs_image()
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    try:
        # /home/nhp/project is a real path on the host; the sandbox
        # container has no bind mount for it and no user 'nhp', so the
        # path must not be reachable (either the dir is missing, or it
        # exists but is empty inside the image).
        res = exec_in(
            cid,
            ["sh", "-c", "ls /home/nhp/project 2>/dev/null"],
            timeout_s=10,
        )
        # Either ls failed (path missing) OR succeeded but with empty
        # output (we definitely shouldn't see the host's repo contents).
        assert res.stdout.strip() == "", (
            f"container saw host path it shouldn't have: stdout={res.stdout!r}"
        )
    finally:
        stop_session_container(cid)


def test_gis_imports_work() -> None:
    """Smoke-test that the pre-warmed GIS stack imports under `uv run`.

    The Dockerfile caches wheels via a PEP 723 script but does not
    install them into the system Python — the agent is expected to
    invoke them via `uv run --with` (or its own PEP 723 script), which
    resolves from the cached wheels and is therefore fast.

    `pyrosm` is intentionally not pre-warmed (its build dep `pyrobuf` is
    incompatible with Python 3.14 — see sandbox/Dockerfile note).
    """
    _needs_image()
    session_id = uuid.uuid4().hex
    cid = start_session_container(session_id=session_id)
    try:
        res = exec_in(
            cid,
            [
                "uv", "run",
                "--with", "geopandas",
                "--with", "shapely",
                "--with", "pyproj",
                "--with", "pyogrio",
                "--with", "fiona",
                "--with", "pandas",
                "--with", "pyarrow",
                "--with", "duckdb",
                "--with", "osmnx",
                "--with", "ftfy",
                "python", "-c",
                "import geopandas, shapely, pyproj, pyogrio, fiona, "
                "pandas, pyarrow, duckdb, osmnx, ftfy",
            ],
            timeout_s=120,
        )
        assert res.returncode == 0, (
            f"GIS imports failed: stdout={res.stdout!r} stderr={res.stderr!r}"
        )
    finally:
        stop_session_container(cid)


def test_exec_on_missing_container_raises() -> None:
    # No image needed — we're testing the inspect-guard path.
    bogus = "definitely-not-a-real-container-" + uuid.uuid4().hex
    with pytest.raises(RuntimeError, match="does not exist"):
        exec_in(bogus, ["echo", "hi"], timeout_s=5)


def test_copy_into_on_missing_container_raises(tmp_path: Path) -> None:
    bogus = "definitely-not-a-real-container-" + uuid.uuid4().hex
    src = tmp_path / "x.txt"
    src.write_text("x")
    with pytest.raises(RuntimeError, match="does not exist"):
        copy_into(bogus, src, "/work")


def test_copy_from_on_missing_container_raises(tmp_path: Path) -> None:
    bogus = "definitely-not-a-real-container-" + uuid.uuid4().hex
    with pytest.raises(RuntimeError, match="does not exist"):
        copy_from(bogus, "/work/x.txt", tmp_path / "x.txt")


def test_stop_is_idempotent_on_missing_container() -> None:
    bogus = "definitely-not-a-real-container-" + uuid.uuid4().hex
    # Should not raise.
    stop_session_container(bogus)
