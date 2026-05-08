"""
ASGI application entry point.

Wires:
  * security headers + request-id middleware
  * CORS (front-end origin only)
  * IP-based rate limiting (slowapi) — additive to Cloud Armor
  * routers: /health, /v1/trips
  * shared service instances on app.state (single-flight per worker)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import firebase_admin  # type: ignore[import-untyped]
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.middleware.security import SecurityHeadersMiddleware
from app.routers import health, trips
from app.services.firestore_service import FirestoreService
from app.services.gemini_service import GeminiService
from app.services.places_service import PlacesService
from app.services.pubsub_service import PubSubService
from app.utils.logger import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    log = get_logger(__name__)

    # Firebase Admin uses Application Default Credentials on Cloud Run.
    if not firebase_admin._apps and not settings.AUTH_DISABLED:
        firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID or settings.GCP_PROJECT})

    app.state.settings = settings
    app.state.gemini = GeminiService(settings)
    app.state.firestore = FirestoreService()
    app.state.places = PlacesService(settings)
    app.state.pubsub = PubSubService(settings)
    log.info("startup", env=settings.ENV)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    )

    app = FastAPI(
        title="Wanderly Trip API",
        version="1.0.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=600,
    )

    app.include_router(health.router)
    app.include_router(trips.router)

    @app.get("/")
    async def _root(request: Request) -> dict[str, str]:
        return {"app": "wanderly", "version": "1.0.0", "env": settings.ENV}

    return app


app = create_app()
