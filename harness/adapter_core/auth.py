"""Optional bearer-token middleware. Off unless HARNESS_BEARER_TOKEN is set."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {token}"

    async def dispatch(self, request: Request, call_next):
        # Health is always public so container orchestrators can probe it.
        if request.url.path == "/health":
            return await call_next(request)
        header = request.headers.get("authorization")
        if header != self._expected:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
