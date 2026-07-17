"""
Background planning-task tests.

The trip is created with status=planning and finished asynchronously. These
tests verify that the trip always leaves the `planning` state — reaching
`ready` on success and `failed` on *any* error, so the client never waits
forever. (TestClient runs FastAPI background tasks before returning.)
"""

from __future__ import annotations

from app.services.gemini_service import GeminiUnavailable

VALID_BODY = {
    "destination": "Manali",
    "start_date": "2026-06-01",
    "end_date": "2026-06-04",
    "travelers": 2,
    "constraints": {"budget_total_inr": 50000},
}


def test_planning_success_marks_ready(client):
    trip_id = client.post("/v1/trips", json=VALID_BODY).json()["id"]
    assert client.get(f"/v1/trips/{trip_id}").json()["status"] == "ready"


def test_gemini_failure_marks_trip_failed(client, app):
    app.state.gemini.generate_itinerary.side_effect = GeminiUnavailable("model down")
    trip_id = client.post("/v1/trips", json=VALID_BODY).json()["id"]
    assert client.get(f"/v1/trips/{trip_id}").json()["status"] == "failed"


def test_unexpected_enrichment_failure_marks_trip_failed(client, app):
    """A non-Gemini error (e.g. Maps enrichment) must still fail the trip."""
    app.state.places.enrich.side_effect = RuntimeError("maps outage")
    trip_id = client.post("/v1/trips", json=VALID_BODY).json()["id"]
    assert client.get(f"/v1/trips/{trip_id}").json()["status"] == "failed"


def test_list_trips_returns_created_trips(client):
    client.post("/v1/trips", json=VALID_BODY)
    client.post("/v1/trips", json=VALID_BODY)
    trips = client.get("/v1/trips").json()
    assert len(trips) >= 2
    assert all(t["user_id"] == "test-user" for t in trips)
