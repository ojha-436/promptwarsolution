"""
Security-headers + request-id middleware.

Sets the security headers Cloud Armor / WAF guides recommend:
* Strict-Transport-Security
* X-Content-Type-Options: nosniff
* X-Frame-Options: DENY
* Referrer-Policy: strict-origin-when-cross-origin
* Permissions-Policy: minimal
* Content-Security-Policy: very tight; the API serves JSON only.

Also stamps `X-Request-ID` so any browser network panel call can be matched
to a Cloud Logging line.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    HEADERS = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none';",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        for k, v in self.HEADERS.items():
            response.headers.setdefault(k, v)
        response.headers["X-Request-ID"] = request_id
        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """
    Reject oversized request bodies up front (HTTP 413) based on the
    Content-Length header, before the body is buffered or parsed. A cheap
    defence-in-depth guard against memory-exhaustion payloads.
    """

    def __init__(self, app: object, max_bytes: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self._max_bytes:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)
