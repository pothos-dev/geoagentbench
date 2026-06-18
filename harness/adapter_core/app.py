"""FastAPI app factory implementing the seven-endpoint contract.

Adapters call ``create_app(run_fn=..., adapter_name=..., adapter_version=...)``
and serve the returned app under uvicorn. The factory wires the contract
endpoints to a SessionStore that drives ``run_fn`` per message.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.datastructures import UploadFile

from adapter_core.auth import BearerAuthMiddleware
from adapter_core.schemas import (
    FilesListResponse,
    HealthResponse,
    MessageRequest,
    MessagesResponse,
    SessionCreatedResponse,
    SessionStatusResponse,
)
from adapter_core.sessions import ContainerBackend, RunFn, SessionStore

ModelValidator = Callable[[str], None]
"""Optional ``X-Harness-Model`` validator. Raises ``ValueError`` (or any
subclass) with a human-readable message when the model id is not supported;
the HTTP layer surfaces the message as a 400 Bad Request. ``None`` means
"accept any non-empty string"."""

log = logging.getLogger(__name__)


def _err(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _safe_basename(name: str) -> str | None:
    """Reject path-traversal, separators, NUL bytes; return the basename or None."""
    if not name or "\x00" in name:
        return None
    if name in (".", "..") or "/" in name or "\\" in name:
        return None
    return name


def create_app(
    run_fn: RunFn,
    adapter_name: str,
    adapter_version: str,
    model_validator: ModelValidator | None = None,
    container_backend: ContainerBackend | None = None,
) -> FastAPI:
    sessions_root = Path(
        os.environ.get(
            "HARNESS_SESSIONS_DIR",
            str(Path(__file__).resolve().parent.parent / ".sessions"),
        )
    ).resolve()
    max_concurrent = int(os.environ.get("HARNESS_MAX_CONCURRENT_SESSIONS", "4"))
    bearer_token = os.environ.get("HARNESS_BEARER_TOKEN")

    store = SessionStore(
        sessions_root=sessions_root,
        max_concurrent=max_concurrent,
        adapter_version=adapter_version,
        container_backend=container_backend,
    )

    app = FastAPI(title=f"{adapter_name} adapter", version=adapter_version)

    if bearer_token:
        app.add_middleware(BearerAuthMiddleware, token=bearer_token)

    # ------------------------------------------------------------------ /health
    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", adapter=adapter_name, version=adapter_version)

    # ----------------------------------------------------------- POST /sessions
    @app.post("/sessions", status_code=201, response_model=SessionCreatedResponse)
    async def create_session(request: Request) -> JSONResponse:
        # Validate the model header *before* allocating a session so a
        # rejected request doesn't leak a work_dir / sandbox container.
        model = (request.headers.get("x-harness-model") or "").strip()
        if not model:
            return _err("X-Harness-Model header is required", 400)
        if model_validator is not None:
            try:
                model_validator(model)
            except ValueError as exc:
                return _err(str(exc), 400)

        label = (request.headers.get("x-harness-label") or "").strip() or None
        session = await store.create(label=label)
        if session is None:
            return JSONResponse(
                {"error": "concurrency limit reached"},
                status_code=503,
                headers={"Retry-After": "5"},
            )
        session.model_override = model
        variant = request.headers.get("x-harness-prompt-variant")
        if variant:
            session.prompt_variant = variant.strip() or None
        return JSONResponse({"session_id": session.session_id}, status_code=201)

    # -------------------------------------------------- POST /sessions/{id}/files
    @app.post("/sessions/{session_id}/files", status_code=204)
    async def upload_files(session_id: str, request: Request) -> Response:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        async with session.lock:
            if session.status == "running":
                return _err("session is running", 409)

        form = await request.form()
        # Collect all UploadFile parts (regardless of field key — original
        # filename is what matters per the contract).
        files = [v for _, v in form.multi_items() if isinstance(v, UploadFile)]
        if not files:
            return _err("no files in request", 400)

        for part in files:
            name = _safe_basename(part.filename or "")
            if name is None:
                return _err(f"invalid filename: {part.filename!r}", 400)
            target = session.work_dir / name
            with target.open("wb") as f:
                while True:
                    chunk = await part.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        session.last_activity_at = session.created_at  # touched, but no event
        return Response(status_code=204)

    # --------------------------------------------- POST /sessions/{id}/messages
    @app.post("/sessions/{session_id}/messages", status_code=202)
    async def post_message(session_id: str, body: MessageRequest) -> Response:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        async with session.lock:
            if session.status == "running":
                return _err("session is running", 409)
            session.message_received = True
            # Synthesize the user-turn text event before the agent runs, so
            # the question is recoverable even if the agent crashes.
            session.append_event(type="text", role="user", content=body.instruction)
            await store.run_message(session, body.instruction, run_fn)
        return Response(status_code=202)

    # ----------------------------------------------------- GET /sessions/{id}
    @app.get("/sessions/{session_id}", response_model=SessionStatusResponse)
    async def get_session(session_id: str) -> JSONResponse:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        body = SessionStatusResponse(
            session_id=session.session_id,
            status=session.status,
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            error=session.error,
            usage=session.usage,
        )
        return JSONResponse(body.model_dump(), status_code=200)

    # ------------------------------------------------ GET /sessions/{id}/files
    @app.get("/sessions/{session_id}/files", response_model=FilesListResponse)
    async def list_files(session_id: str) -> JSONResponse:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        names = sorted(
            p.name for p in session.work_dir.iterdir() if p.is_file()
        )
        return JSONResponse({"files": names}, status_code=200)

    # --------------------------------------- GET /sessions/{id}/files/{filename}
    @app.get("/sessions/{session_id}/files/{filename}")
    async def get_file(session_id: str, filename: str) -> Response:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        name = _safe_basename(filename)
        if name is None:
            return _err("invalid filename", 400)
        path = session.work_dir / name
        if not path.is_file():
            return _err("file not found", 404)
        return FileResponse(
            path,
            media_type="application/octet-stream",
            filename=name,
        )

    # --------------------------------------------- GET /sessions/{id}/messages
    @app.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
    async def get_messages(session_id: str) -> JSONResponse:
        session = store.get(session_id)
        if session is None:
            return _err("session not found", 404)
        return JSONResponse(
            {"events": [e.model_dump() for e in session.events]},
            status_code=200,
        )

    # ------------------------------------------------------ DELETE /sessions/{id}
    @app.delete("/sessions/{session_id}", status_code=204)
    async def delete_session(session_id: str) -> Response:
        deleted = await store.delete(session_id)
        if not deleted:
            return _err("session not found", 404)
        return Response(status_code=204)

    return app
