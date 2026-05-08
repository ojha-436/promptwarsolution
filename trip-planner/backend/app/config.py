"""
Centralised, typed configuration following 12-factor principles.

All values come from environment variables. Secrets are never committed.
Production reads sensitive values from Secret Manager via Cloud Run env-var
references (e.g. GEMINI_API_KEY: projects/$PROJECT/secrets/gemini-api-key).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────
    APP_NAME: str = "wanderly-api"
    ENV: Literal["dev", "staging", "prod"] = "dev"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8080

    # ── GCP ───────────────────────────────────────────────────────────────
    GCP_PROJECT: str = Field(..., description="GCP project ID")
    GCP_REGION: str = "asia-south1"
    PUBSUB_TRIP_EVENTS_TOPIC: str = "trip-events"

    # ── AI ────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(..., description="Vertex AI / Gemini API key")
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_MAX_OUTPUT_TOKENS: int = 4096
    GEMINI_TEMPERATURE: float = 0.7

    # ── Maps ──────────────────────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str = ""
    AUTH_DISABLED: bool = False  # tests only

    # ── Limits ────────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30
    MAX_TRIP_DAYS: int = 30
    MAX_TRAVELERS: int = 12

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read once per process."""
    return Settings()  # type: ignore[call-arg]
