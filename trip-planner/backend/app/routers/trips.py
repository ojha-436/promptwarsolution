"""
/v1/trips — the core router.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.middleware.auth import AuthenticatedUser, get_current_user
from app.models import (
    EventType,
    Trip,
    TripEvent,
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
    return request.app.state.firestore


def _gemini(request: Request) -> GeminiService:
    return request.app.state.gemini


def _places(request: Request) -> PlacesService:
    return request.app.state.places


def _pubsub(request: Request) -> PubSubService:
    return request.app.state.pubsub


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
    now = datetime.now(tz=timezone.utc)
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
        trip.updated_at = datetime.now(tz=timezone.utc)
        fs.save(trip)
        log.info("trip.ready", trip_id=trip.id)
    except GeminiUnavailable as exc:
        log.error("trip.failed", trip_id=trip.id, error=str(exc))
        fs.update_status(trip.user_id, trip.id, TripStatus.FAILED)


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(
    trip_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
) -> Trip:
    trip = fs.get(user.uid, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trip not found")
    return trip


@router.get("", response_model=list[Trip])
async def list_trips(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
) -> list[Trip]:
    return fs.list_for_user(user.uid)


@router.post("/{trip_id}/events", status_code=status.HTTP_202_ACCEPTED)
async def push_event(
    trip_id: str,
    body: dict,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    fs: Annotated[FirestoreService, Depends(_firestore)],
    pubsub: Annotated[PubSubService, Depends(_pubsub)],
) -> dict:
    """
    Inject a real-time event (user-edit, weather, flight delay).

    The user-edit type is the user changing the plan; weather/flight come from
    Cloud Scheduler / webhooks. All paths funnel through Pub/Sub so the same
    re-plan worker handles everything uniformly.
    """
    trip = fs.get(user.uid, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trip not found")

    try:
        event_type = EventType(body.get("type", ""))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid event type") from exc

    event = TripEvent(
        type=event_type,
        trip_id=trip_id,
        payload=body.get("payload", {}),
        occurred_at=datetime.now(tz=timezone.utc),
    )
    fs.update_status(user.uid, trip_id, TripStatus.UPDATING)
    msg_id = pubsub.publish_event(event)
    return {"message_id": msg_id, "trip_id": trip_id, "status": "updating"}
