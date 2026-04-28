import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.config import (
    RATE_LIMIT_AUTH_MAX_REQUESTS,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window_seconds = RATE_LIMIT_WINDOW_SECONDS
        self.default_limit = RATE_LIMIT_MAX_REQUESTS
        self.auth_limit = RATE_LIMIT_AUTH_MAX_REQUESTS
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _limit_for_path(self, path: str) -> int:
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
            return self.auth_limit
        return self.default_limit

    def _key_for_request(self, request: Request) -> str:
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{request.url.path}"

    def _is_exempt(self, request: Request) -> bool:
        return request.url.path in {"/", "/healthz"} or request.method == "OPTIONS"

    async def dispatch(self, request: Request, call_next):
        if self._is_exempt(request):
            return await call_next(request)

        key = self._key_for_request(request)
        now = time.time()
        window_start = now - self.window_seconds
        entries = self._hits[key]
        while entries and entries[0] <= window_start:
            entries.popleft()

        limit = self._limit_for_path(request.url.path)
        if len(entries) >= limit:
            retry_after = max(1, int(entries[0] + self.window_seconds - now))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"detail": "Rate limit exceeded. Please retry later."},
            )

        entries.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(entries)))
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        return response
