"""Security regression tests — these failing means a real risk has shipped."""

from __future__ import annotations


def test_security_headers_set(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "max-age" in r.headers["Strict-Transport-Security"]
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert "X-Request-ID" in r.headers


def test_request_id_propagates(client):
    r = client.get("/health", headers={"X-Request-ID": "trace-abc"})
    assert r.headers["X-Request-ID"] == "trace-abc"


def test_huge_payload_rejected(client):
    body = {
        "destination": "X" * 200,  # > max_length 120
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "travelers": 2,
        "constraints": {"budget_total_inr": 20000},
    }
    r = client.post("/v1/trips", json=body)
    assert r.status_code == 422


def test_must_avoid_clamped(client):
    body = {
        "destination": "Goa",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "travelers": 2,
        "constraints": {
            "budget_total_inr": 20000,
            "must_avoid": [f"x{i}" for i in range(50)],  # > max_length 20
        },
    }
    r = client.post("/v1/trips", json=body)
    assert r.status_code == 422


def test_no_token_required_path_does_not_leak_internals(client):
    """404 must not reveal whether the resource exists for another user."""
    r = client.get("/v1/trips/some-other-users-trip")
    assert r.status_code == 404
    assert "user" not in r.json().get("detail", "").lower()


def test_oversized_request_body_rejected_with_413(client):
    """A body over the configured limit is rejected before parsing."""
    oversized = {"notes": "A" * 300_000}  # ~300 KB > 256 KiB limit
    r = client.post("/v1/trips", json=oversized)
    assert r.status_code == 413
    assert r.json()["detail"] == "request body too large"


def test_normal_body_not_rejected_by_size_guard(client):
    """A normally-sized valid request passes the size guard."""
    body = {
        "destination": "Goa",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03",
        "travelers": 2,
        "constraints": {"budget_total_inr": 20000},
    }
    r = client.post("/v1/trips", json=body)
    assert r.status_code == 202
