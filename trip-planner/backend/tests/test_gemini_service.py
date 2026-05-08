"""GeminiService unit tests — entirely mocked, no network."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.models import Constraints, Itinerary, Preferences, TripRequest
from app.services.gemini_service import GeminiService, GeminiUnavailable


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
