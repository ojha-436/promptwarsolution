"""Integration tests for /v1/trips."""

from __future__ import annotations

VALID_BODY = {
    "destination": "Manali",
    "start_date": "2026-06-01",
    "end_date": "2026-06-04",
    "travelers": 2,
    "preferences": {"interests": ["nature"]},
    "constraints": {"budget_total_inr": 50000},
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_trip_returns_202(client):
    r = client.post("/v1/trips", json=VALID_BODY)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] in ("planning", "ready")
    assert body["user_id"] == "test-user"
    assert body["request"]["destination"] == "Manali"


def test_create_trip_rejects_bad_dates(client):
    bad = dict(VALID_BODY)
    bad["end_date"] = "2026-05-30"
    r = client.post("/v1/trips", json=bad)
    assert r.status_code == 422


def test_create_trip_rejects_extra_fields(client):
    bad = dict(VALID_BODY)
    bad["__proto__"] = "polluted"
    r = client.post("/v1/trips", json=bad)
    assert r.status_code == 422


def test_get_trip_404(client):
    r = client.get("/v1/trips/does-not-exist")
    assert r.status_code == 404


def test_create_then_get(client):
    r = client.post("/v1/trips", json=VALID_BODY)
    trip_id = r.json()["id"]
    g = client.get(f"/v1/trips/{trip_id}")
    assert g.status_code == 200
    assert g.json()["id"] == trip_id


def test_event_endpoint_publishes(client, app):
    r = client.post("/v1/trips", json=VALID_BODY)
    trip_id = r.json()["id"]
    e = client.post(
        f"/v1/trips/{trip_id}/events",
        json={"type": "weather", "payload": {"day": 2, "condition": "rain"}},
    )
    assert e.status_code == 202
    assert e.json()["message_id"] == "msg-1"
    app.state.pubsub.publish_event.assert_called_once()


def test_event_endpoint_rejects_invalid_type(client):
    r = client.post("/v1/trips", json=VALID_BODY)
    trip_id = r.json()["id"]
    bad = client.post(f"/v1/trips/{trip_id}/events", json={"type": "WAT"})
    assert bad.status_code == 422
