"""
Rate-limiting regression tests.

The application configures a slowapi Limiter, but a limiter only *enforces*
anything when `SlowAPIMiddleware` is installed. These tests guard both:
the wiring in `create_app`, and the actual 429 behaviour end-to-end.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.main import create_app


def test_create_app_installs_slowapi_middleware():
    """Regression guard: the enforcing middleware must be wired in."""
    app = create_app()
    assert any(m.cls is SlowAPIMiddleware for m in app.user_middleware), (
        "SlowAPIMiddleware missing — the configured rate limit would be inert"
    )


def test_requests_over_limit_return_429():
    """A client exceeding the per-minute budget receives HTTP 429."""
    limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as c:
        statuses = [c.get("/ping").status_code for _ in range(7)]

    assert statuses.count(200) == 5
    assert statuses.count(429) == 2
