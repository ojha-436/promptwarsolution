"""
Pydantic v2 schemas for the Trip domain.

These are the contract between the API, the LLM (via structured output),
the data store, and the frontend. They are intentionally strict — invalid
input is rejected at the boundary, never reaches Gemini, and never reaches
Firestore.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Enums ──────────────────────────────────────────────────────────────────


class TravelStyle(str, Enum):
    BUDGET = "budget"
    BALANCED = "balanced"
    LUXURY = "luxury"


class Pace(str, Enum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"


class DietaryNeed(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    KOSHER = "kosher"
    GLUTEN_FREE = "gluten_free"
    NUT_FREE = "nut_free"


class MobilityNeed(str, Enum):
    NONE = "none"
    WHEELCHAIR = "wheelchair"
    LIMITED_WALKING = "limited_walking"


class TripStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    READY = "ready"
    UPDATING = "updating"
    FAILED = "failed"


class EventType(str, Enum):
    WEATHER = "weather"
    FLIGHT_DELAY = "flight_delay"
    CLOSURE = "closure"
    USER_EDIT = "user_edit"


# ── Inputs ─────────────────────────────────────────────────────────────────


class Constraints(BaseModel):
    """Hard, non-negotiable limits on the trip."""

    model_config = ConfigDict(extra="forbid")

    budget_total_inr: Annotated[int, Field(ge=1000, le=10_000_000)]
    max_daily_walking_km: Annotated[float, Field(ge=0, le=50)] = 8.0
    must_include: list[str] = Field(default_factory=list, max_length=20)
    must_avoid: list[str] = Field(default_factory=list, max_length=20)
    accessibility: MobilityNeed = MobilityNeed.NONE


class Preferences(BaseModel):
    """Soft preferences that shape the plan."""

    model_config = ConfigDict(extra="forbid")

    style: TravelStyle = TravelStyle.BALANCED
    pace: Pace = Pace.MODERATE
    interests: list[str] = Field(default_factory=list, max_length=15)
    dietary: list[DietaryNeed] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"], max_length=5)


class TripRequest(BaseModel):
    """Payload to POST /v1/trips."""

    model_config = ConfigDict(extra="forbid")

    destination: Annotated[str, Field(min_length=2, max_length=120)]
    start_date: date
    end_date: date
    travelers: Annotated[int, Field(ge=1, le=12)]
    preferences: Preferences = Preferences()
    constraints: Constraints
    notes: Annotated[str, Field(max_length=500)] = ""

    @model_validator(mode="after")
    def _validate_dates(self) -> TripRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("trip cannot exceed 30 days")
        return self

    @field_validator("destination")
    @classmethod
    def _strip_destination(cls, v: str) -> str:
        return v.strip()


# ── Itinerary (LLM output schema + DB schema) ─────────────────────────────


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=140)]
    description: Annotated[str, Field(max_length=600)]
    start_time: str  # HH:MM
    end_time: str
    location_name: str
    lat: float | None = None
    lng: float | None = None
    estimated_cost_inr: Annotated[int, Field(ge=0)]
    category: Literal[
        "food", "sightseeing", "transit", "rest", "shopping", "activity", "lodging"
    ]
    booking_url: str | None = None
    accessibility_notes: str = ""


class DayPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_index: Annotated[int, Field(ge=1, le=30)]
    date: date
    summary: Annotated[str, Field(max_length=300)]
    activities: list[Activity] = Field(min_length=1, max_length=12)
    daily_walking_km: float = 0.0
    daily_cost_inr: int = 0


class Itinerary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str
    start_date: date
    end_date: date
    days: list[DayPlan]
    total_cost_inr: int
    summary: Annotated[str, Field(max_length=600)]
    warnings: list[str] = Field(default_factory=list)


class Trip(BaseModel):
    """Stored representation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    status: TripStatus
    request: TripRequest
    itinerary: Itinerary | None = None
    created_at: datetime
    updated_at: datetime
    version: int = 1


# ── Real-time events ──────────────────────────────────────────────────────


class TripEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EventType
    trip_id: str
    payload: dict[str, str | int | float | bool] = Field(default_factory=dict)
    occurred_at: datetime
