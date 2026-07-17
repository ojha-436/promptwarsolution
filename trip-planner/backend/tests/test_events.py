"""
Validation tests for POST /v1/trips/{id}/events.

This endpoint used to accept a free-form dict; it now binds to the strict
`TripEventRequest` model. These tests lock that contract in.
"""

from __future__ import annotations

VALID_BODY = {
    "destination": "Manali",
    "start_date": "2026-06-01",
    "end_date": "2026-06-04",
    "travelers": 2,
    "preferences": {"interests": ["nature"]},
    "constraints": {"budget_total_inr": 50000},
}


def _create_trip(client) -> str:
    return client.post("/v1/trips", json=VALID_BODY).json()["id"]


def test_valid_user_edit_event_accepted(client, app):
    trip_id = _create_trip(client)
    r = client.post(
        f"/v1/trips/{trip_id}/events",
        json={"type": "user_edit", "payload": {"day": 2, "swap": "museum"}},
    )
    assert r.status_code == 202
    assert r.json()["status"] == "updating"
    app.state.pubsub.publish_event.assert_called_once()


def test_event_rejects_extra_field(client):
    trip_id = _create_trip(client)
    r = client.post(
        f"/v1/trips/{trip_id}/events",
        json={"type": "weather", "payload": {}, "injected": "x"},
    )
    assert r.status_code == 422


def test_event_rejects_oversized_payload(client):
    trip_id = _create_trip(client)
    big = {f"k{i}": i for i in range(25)}  # > 20 keys
    r = client.post(f"/v1/trips/{trip_id}/events", json={"type": "weather", "payload": big})
    assert r.status_code == 422


def test_event_rejects_overlong_payload_value(client):
    trip_id = _create_trip(client)
    r = client.post(
        f"/v1/trips/{trip_id}/events",
        json={"type": "weather", "payload": {"note": "x" * 600}},
    )
    assert r.status_code == 422


def test_event_rejects_non_object_payload(client):
    trip_id = _create_trip(client)
    r = client.post(
        f"/v1/trips/{trip_id}/events",
        json={"type": "weather", "payload": "not-an-object"},
    )
    assert r.status_code == 422


def test_event_on_missing_trip_returns_404(client):
    r = client.post("/v1/trips/nope/events", json={"type": "weather"})
    assert r.status_code == 404
