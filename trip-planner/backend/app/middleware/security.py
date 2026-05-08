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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


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

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
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
