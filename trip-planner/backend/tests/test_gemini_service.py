"""GeminiService unit tests — entirely mocked, no network."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.models import Constraints, Itinerary, Preferences, TripRequest
from app.services.gemini_service import (
    GeminiService,
    GeminiTransient,
    GeminiUnavailable,
    _is_transient,
)


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        GCP_PROJECT="t", GEMINI_API_KEY="t",
    )


def _request(budget: int = 50000) -> TripRequest:
    return TripRequest(
        destination="Manali",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        travelers=2,
        preferences=Preferences(),
        constraints=Constraints(budget_total_inr=budget),
    )


def test_generate_itinerary_parses_structured_output(sample_itinerary: Itinerary):
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = sample_itinerary.model_dump_json()
    fake_client.models.generate_content.return_value = fake_resp

    svc = GeminiService(_settings(), client=fake_client)
    out = svc.generate_itinerary(_request())

    assert out.destination == sample_itinerary.destination
    fake_client.models.generate_content.assert_called_once()


def test_generate_itinerary_raises_on_bad_json():
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = "{not valid json"
    fake_client.models.generate_content.return_value = fake_resp

    svc = GeminiService(_settings(), client=fake_client)
    with pytest.raises(GeminiUnavailable):
        svc.generate_itinerary(_request())


def test_budget_overage_recorded_as_warning(sample_itinerary: Itinerary):
    """Even if Gemini ignores budget, our defence-in-depth catches it."""
    sample_itinerary.total_cost_inr = 100000  # over budget
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = sample_itinerary.model_dump_json()
    fake_client.models.generate_content.return_value = fake_resp

    svc = GeminiService(_settings(), client=fake_client)
    out = svc.generate_itinerary(_request(budget=50000))
    assert any("budget" in w.lower() for w in out.warnings)


def test_transient_error_is_retried_then_raised(monkeypatch):
    """A transient (5xx/network) error is retried up to 3 times, then re-raised."""
    monkeypatch.setattr("time.sleep", lambda _s: None)  # don't actually back off
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = TimeoutError("deadline exceeded")

    svc = GeminiService(_settings(), client=fake_client)
    with pytest.raises(GeminiUnavailable):
        svc.generate_itinerary(_request())

    assert fake_client.models.generate_content.call_count == 3


def test_permanent_error_is_not_retried(monkeypatch):
    """A non-transient error (e.g. a 4xx) fails fast without retrying."""
    monkeypatch.setattr("time.sleep", lambda _s: None)
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = ValueError("permission denied")

    svc = GeminiService(_settings(), client=fake_client)
    with pytest.raises(GeminiUnavailable):
        svc.generate_itinerary(_request())

    assert fake_client.models.generate_content.call_count == 1


def test_repair_itinerary_parses_response(sample_itinerary: Itinerary):
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = sample_itinerary.model_dump_json()
    fake_client.models.generate_content.return_value = fake_resp

    svc = GeminiService(_settings(), client=fake_client)
    out = svc.repair_itinerary(sample_itinerary, _request(), reason="Heavy rain on Day 1")

    assert out.destination == sample_itinerary.destination
    fake_client.models.generate_content.assert_called_once()


class _CodedError(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f"http {code}")
        self.code = code


def test_is_transient_classification():
    assert _is_transient(TimeoutError()) is True
    assert _is_transient(ConnectionError()) is True
    assert _is_transient(_CodedError(503)) is True
    assert _is_transient(_CodedError(429)) is True
    assert _is_transient(_CodedError(400)) is False
    assert _is_transient(ValueError("invalid argument")) is False
    assert _is_transient(RuntimeError("503 service unavailable")) is True


def test_transient_subclasses_unavailable():
    """Callers catching GeminiUnavailable also catch the transient give-up."""
    assert issubclass(GeminiTransient, GeminiUnavailable)

