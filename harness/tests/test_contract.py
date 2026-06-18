"""Contract tests using a mock run_fn and a fake container backend —
exercises every endpoint and the state machine without spawning real
docker containers."""

from __future__ import annotations

import asyncio
import io
import os
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from adapter_core.app import create_app
from adapter_core.sessions import Session


class _FakeBackend:
    """In-memory stand-in for the docker-CLI backend.

    Tracks start/stop calls so tests can assert on them; copy_into/copy_from
    are no-ops because the contract tests already write directly to
    ``session.work_dir`` (which is what the agent would see anyway).
    """

    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    def start(self, session_id: str) -> str:
        cid = f"fake-{uuid.uuid4().hex[:12]}"
        self.started.append(cid)
        return cid

    def stop(self, container_id: str) -> None:
        self.stopped.append(container_id)

    def copy_into(self, container_id: str, host_path: Path, container_path: str) -> None:
        pass

    def copy_from(self, container_id: str, container_path: str, host_path: Path) -> None:
        pass


@pytest.fixture
def sessions_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "sessions"
    monkeypatch.setenv("HARNESS_SESSIONS_DIR", str(d))
    monkeypatch.setenv("HARNESS_MAX_CONCURRENT_SESSIONS", "2")
    return d


async def _ok_run(session: Session, instruction: str) -> None:
    session.set_model("test-model")
    session.append_event(type="text", role="assistant", content=f"echo: {instruction}")
    (session.work_dir / "output.txt").write_text(f"result for: {instruction}\n")
    session.add_cost(0.001)


async def _echo_model_run(session: Session, instruction: str) -> None:
    session.set_model(session.model_override or "fallback")
    session.add_cost(0.0)


async def _slow_run(session: Session, instruction: str) -> None:
    await asyncio.sleep(5.0)


async def _fail_run(session: Session, instruction: str) -> None:
    raise RuntimeError("agent went boom")


def _build(run_fn) -> AsyncClient:
    app = create_app(
        run_fn=run_fn,
        adapter_name="test",
        adapter_version="0.0.0",
        container_backend=_FakeBackend(),
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _wait_idle(client: AsyncClient, sid: str, timeout: float = 3.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"/sessions/{sid}")
        body = r.json()
        if body["status"] in ("idle", "failed"):
            return body
        await asyncio.sleep(0.02)
    raise AssertionError(f"session {sid} did not settle within {timeout}s")


MODEL_HDR = {"X-Harness-Model": "test-model"}


async def test_model_header_required(sessions_dir: Path) -> None:
    async with _build(_echo_model_run) as c:
        # without header → 400
        r = await c.post("/sessions")
        assert r.status_code == 400

        # with X-Harness-Model → created and echoed back
        r = await c.post("/sessions", headers={"X-Harness-Model": "haiku"})
        assert r.status_code == 201
        sid = r.json()["session_id"]
        await c.post(f"/sessions/{sid}/messages", json={"instruction": "x"})
        body = await _wait_idle(c, sid)
        assert body["usage"]["model"] == "haiku"


async def test_health(sessions_dir: Path) -> None:
    async with _build(_ok_run) as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


async def test_full_happy_path(sessions_dir: Path) -> None:
    async with _build(_ok_run) as c:
        # create
        r = await c.post("/sessions", headers=MODEL_HDR)
        assert r.status_code == 201
        sid = r.json()["session_id"]

        # upload two files
        files = [
            ("file", ("input.geojson", io.BytesIO(b'{"a":1}'), "application/octet-stream")),
            ("file", ("readme.txt", io.BytesIO(b"hello"), "text/plain")),
        ]
        r = await c.post(f"/sessions/{sid}/files", files=files)
        assert r.status_code == 204

        # list shows both uploaded files (no kind discriminator)
        r = await c.get(f"/sessions/{sid}/files")
        assert r.status_code == 200
        assert sorted(r.json()["files"]) == ["input.geojson", "readme.txt"]

        # send instruction
        r = await c.post(f"/sessions/{sid}/messages", json={"instruction": "do it"})
        assert r.status_code == 202

        # poll → idle
        body = await _wait_idle(c, sid)
        assert body["status"] == "idle"
        assert body["error"] is None
        assert body["usage"]["model"] == "test-model"
        assert body["usage"]["estimated_cost_usd"] > 0

        # generated file appears in flat listing alongside uploads
        r = await c.get(f"/sessions/{sid}/files")
        assert "output.txt" in r.json()["files"]

        # download generated file
        r = await c.get(f"/sessions/{sid}/files/output.txt")
        assert r.status_code == 200
        assert b"result for: do it" in r.content

        # event log contains the synthesized user turn + the assistant text
        r = await c.get(f"/sessions/{sid}/messages")
        events = r.json()["events"]
        roles = [(e["type"], e["role"]) for e in events]
        assert ("text", "user") in roles
        assert ("text", "assistant") in roles

        # delete
        r = await c.delete(f"/sessions/{sid}")
        assert r.status_code == 204

        # gone
        r = await c.get(f"/sessions/{sid}")
        assert r.status_code == 404
        assert not (sessions_dir / sid).exists()


async def test_second_message_accepted_when_idle(sessions_dir: Path) -> None:
    async with _build(_ok_run) as c:
        sid = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        r = await c.post(f"/sessions/{sid}/messages", json={"instruction": "first"})
        assert r.status_code == 202
        await _wait_idle(c, sid)
        # Second message accepted once the session is idle again.
        r = await c.post(f"/sessions/{sid}/messages", json={"instruction": "second"})
        assert r.status_code == 202


async def test_upload_during_running_is_409(sessions_dir: Path) -> None:
    async with _build(_slow_run) as c:
        sid = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        await c.post(f"/sessions/{sid}/messages", json={"instruction": "wait"})
        # Now running — uploads must be rejected.
        files = [("file", ("x.bin", io.BytesIO(b"x"), "application/octet-stream"))]
        r = await c.post(f"/sessions/{sid}/files", files=files)
        assert r.status_code == 409
        await c.delete(f"/sessions/{sid}")


async def test_filename_traversal_rejected(sessions_dir: Path) -> None:
    async with _build(_ok_run) as c:
        sid = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        for bad in ("../escape", "a/b", "..", ""):
            r = await c.post(
                f"/sessions/{sid}/files",
                files=[("file", (bad, io.BytesIO(b"x"), "application/octet-stream"))],
            )
            assert r.status_code == 400, f"expected 400 for {bad!r}"


async def test_failed_session_surfaces_error(sessions_dir: Path) -> None:
    async with _build(_fail_run) as c:
        sid = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        await c.post(f"/sessions/{sid}/messages", json={"instruction": "boom"})
        body = await _wait_idle(c, sid)
        assert body["status"] == "failed"
        assert "boom" in body["error"]
        # History remains available on failure.
        r = await c.get(f"/sessions/{sid}/messages")
        assert r.status_code == 200


async def test_concurrency_limit_returns_503(sessions_dir: Path) -> None:
    async with _build(_slow_run) as c:
        s1 = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        s2 = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        await c.post(f"/sessions/{s1}/messages", json={"instruction": "a"})
        await c.post(f"/sessions/{s2}/messages", json={"instruction": "b"})
        # Both running; third create must hit the limit.
        r = await c.post("/sessions", headers=MODEL_HDR)
        assert r.status_code == 503
        assert r.headers.get("Retry-After") == "5"
        await c.delete(f"/sessions/{s1}")
        await c.delete(f"/sessions/{s2}")


async def test_delete_cancels_running(sessions_dir: Path) -> None:
    async with _build(_slow_run) as c:
        sid = (await c.post("/sessions", headers=MODEL_HDR)).json()["session_id"]
        await c.post(f"/sessions/{sid}/messages", json={"instruction": "long"})
        r = await c.delete(f"/sessions/{sid}")
        assert r.status_code == 204
        r = await c.get(f"/sessions/{sid}")
        assert r.status_code == 404


async def test_unknown_session_404(sessions_dir: Path) -> None:
    async with _build(_ok_run) as c:
        for path in (
            "/sessions/missing",
            "/sessions/missing/files",
            "/sessions/missing/messages",
            "/sessions/missing/files/x",
        ):
            r = await c.get(path)
            assert r.status_code == 404


async def test_bearer_auth_when_set(sessions_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARNESS_BEARER_TOKEN", "s3cret")
    async with _build(_ok_run) as c:
        # Health stays public.
        assert (await c.get("/health")).status_code == 200
        # Other endpoints require the bearer.
        assert (await c.post("/sessions", headers=MODEL_HDR)).status_code == 401
        r = await c.post("/sessions", headers={**MODEL_HDR, "authorization": "Bearer s3cret"})
        assert r.status_code == 201
