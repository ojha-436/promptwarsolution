"""
Shared test fixtures.

We mock all external SDKs so tests run in <1s without GCP credentials.
The application code never sees the difference because services are
injected via app.state.
"""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Tell config.py we're in test mode before importing the app
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")

from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402
    Activity,
    Constraints,
    DayPlan,
    Itinerary,
    Preferences,
    TripRequest,
    TripStatus,
)


@pytest.fixture
def sample_request() -> TripRequest:
    return TripRequest(
        destination="Manali",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 4),
        travelers=2,
        preferences=Preferences(interests=["nature", "food"]),
        constraints=Constraints(budget_total_inr=50000, accessibility="none"),
        notes="prefer mornings",
    )


@pytest.fixture
def sample_itinerary() -> Itinerary:
    return Itinerary(
        destination="Manali",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 4),
        days=[
            DayPlan(
                day_index=1,
                date=date(2026, 6, 1),
                summary="Arrival and Mall Road",
                activities=[
                    Activity(
                        title="Arrive in Manali",
                        description="Check into hotel.",
                        start_time="14:00",
                        end_time="15:00",
                        location_name="Hotel",
                        estimated_cost_inr=3000,
                        category="lodging",
                    )
                ],
                daily_walking_km=1.0,
                daily_cost_inr=3000,
            )
        ],
        total_cost_inr=3000,
        summary="A short Manali trip.",
    )


@pytest.fixture
def app(sample_itinerary):
    app = create_app()

    # Replace external services with mocks
    fake_gemini = MagicMock()
    fake_gemini.generate_itinerary.return_value = sample_itinerary
    fake_gemini.repair_itinerary.return_value = sample_itinerary

    fake_firestore = MagicMock()
    fake_firestore._store = {}

    def _save(trip):
        fake_firestore._store[(trip.user_id, trip.id)] = trip

    def _get(uid, tid):
        return fake_firestore._store.get((uid, tid))

    def _list(uid, limit=50):
        return [t for (u, _), t in fake_firestore._store.items() if u == uid]

    def _update_status(uid, tid, status):
        if (uid, tid) in fake_firestore._store:
            trip = fake_firestore._store[(uid, tid)]
            trip.status = status

    fake_firestore.save.side_effect = _save
    fake_firestore.get.side_effect = _get
    fake_firestore.list_for_user.side_effect = _list
    fake_firestore.update_status.side_effect = _update_status

    fake_pubsub = MagicMock()
    fake_pubsub.publish_event.return_value = "msg-1"

    fake_places = MagicMock()
    fake_places.enrich.side_effect = lambda x: x

    app.state.gemini = fake_gemini
    app.state.firestore = fake_firestore
    app.state.pubsub = fake_pubsub
    app.state.places = fake_places
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
