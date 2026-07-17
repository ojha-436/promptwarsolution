"""
/v1/trips — the core router.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.middleware.auth import AuthenticatedUser, get_current_user
from app.models import (
    Trip,
    TripEvent,
    TripEventRequest,
    TripRequest,
    TripStatus,
)
from app.services.firestore_service import FirestoreService
from app.services.gemini_service import GeminiService, GeminiUnavailable
from app.services.places_service import PlacesService
from app.services.pubsub_service import PubSubService
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/v1/trips", tags=["trips"])


# ── Dependency wiring ──────────────────────────────────────────────────────


def _firestore(request: Request) -> FirestoreService:
    return cast(FirestoreService, request.app.state.firestore)


def _gemini(request: Request) -> GeminiService:
    return cast(GeminiService, request.app.state.gemini)


def _places(request: Request) -> PlacesService:
    return cast(PlacesService, request.app.state.places)


def _pubsub(request: Request) -> PubSubService:
    return cast(PubSubService, request.app.state.pubsub)


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Trip)
async def create_trip(
    body: TripRequest,
    background: BackgroundTasks,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
    gemini: Annotated[GeminiService, Depends(_gemini)],
    places: Annotated[PlacesService, Depends(_places)],
) -> Trip:
    """
    Create a new trip. Returns 202 immediately with status=PLANNING; Gemini
    runs in the background and the client subscribes to Firestore for the
    final READY/ FAILED state.
    """
    now = datetime.now(tz=UTC)
    trip = Trip(
        id=uuid.uuid4().hex,
        user_id=user.uid,
        status=TripStatus.PLANNING,
        request=body,
        itinerary=None,
        created_at=now,
        updated_at=now,
        version=1,
    )
    fs.save(trip)

    background.add_task(_run_planning, trip, fs, gemini, places)
    return trip


def _run_planning(
    trip: Trip,
    fs: FirestoreService,
    gemini: GeminiService,
    places: PlacesService,
) -> None:
    try:
        itinerary = gemini.generate_itinerary(trip.request)
        itinerary = places.enrich(itinerary)
        trip.itinerary = itinerary
        trip.status = TripStatus.READY
        trip.updated_at = datetime.now(tz=UTC)
        fs.save(trip)
        log.info("trip.ready", trip_id=trip.id)
    except GeminiUnavailable as exc:
        # Expected failure mode: the model was unreachable or returned bad output.
        log.error("trip.failed", trip_id=trip.id, error=str(exc))
        fs.update_status(trip.user_id, trip.id, TripStatus.FAILED)
    except Exception as exc:  # noqa: BLE001 — a background task must never leave a trip stuck
        # Any other failure (e.g. Maps enrichment, Firestore write) must still
        # transition the trip out of PLANNING so the client stops waiting.
        log.error("trip.failed.unexpected", trip_id=trip.id, error=str(exc))
        try:
            fs.update_status(trip.user_id, trip.id, TripStatus.FAILED)
        except Exception:  # noqa: BLE001 — last-resort guard; nothing else we can do
            log.error("trip.failed.status_update_failed", trip_id=trip.id)


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(
    trip_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
) -> Trip:
    """Fetch one trip by id, scoped to the authenticated user (404 if absent)."""
    trip = fs.get(user.uid, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trip not found")
    return trip


@router.get("", response_model=list[Trip])
async def list_trips(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
) -> list[Trip]:
    """List the authenticated user's trips, newest first."""
    return fs.list_for_user(user.uid)


@router.post("/{trip_id}/events", status_code=status.HTTP_202_ACCEPTED)
async def push_event(
    trip_id: str,
    body: TripEventRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
    pubsub: Annotated[PubSubService, Depends(_pubsub)],
) -> dict[str, str]:
    """
    Inject a real-time event (user-edit, weather, flight delay).

    The body is validated against `TripEventRequest`, so an unknown event type,
    an extra field, or an oversized payload is rejected with 422 automatically
    — the endpoint no longer parses a free-form dict by hand.

    The user-edit type is the user changing the plan; weather/flight come from
    Cloud Scheduler / webhooks. All paths funnel through Pub/Sub so the same
    re-plan worker handles everything uniformly.
    """
    trip = fs.get(user.uid, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trip not found")

    event = TripEvent(
        type=body.type,
        trip_id=trip_id,
        payload=body.payload,
        occurred_at=datetime.now(tz=UTC),
    )
    fs.update_status(user.uid, trip_id, TripStatus.UPDATING)
    msg_id = pubsub.publish_event(event)
    return {"message_id": msg_id, "trip_id": trip_id, "status": "updating"}
