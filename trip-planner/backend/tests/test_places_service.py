"""
PlacesService (Maps enrichment) unit tests — fully mocked, no network.

Enrichment is the post-LLM hallucination guard: it geocodes venue names and
leaves coordinates null (a signal) when a venue can't be resolved.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.config import Settings
from app.services.places_service import PlacesService


def _settings(maps_key: str = "maps-test-key") -> Settings:
    return Settings(  # type: ignore[call-arg]
        GCP_PROJECT="t", GEMINI_API_KEY="t", GOOGLE_MAPS_API_KEY=maps_key
    )


def test_enrich_attaches_coordinates(sample_itinerary):
    client = MagicMock()
    client.geocode.return_value = [{"geometry": {"location": {"lat": 32.24, "lng": 77.18}}}]
    svc = PlacesService(_settings(), client=client)

    out = svc.enrich(sample_itinerary)

    act = out.days[0].activities[0]
    assert act.lat == 32.24
    assert act.lng == 77.18
    client.geocode.assert_called_once()


def test_unresolvable_venue_leaves_coordinates_null(sample_itinerary):
    client = MagicMock()
    client.geocode.return_value = []  # nothing found
    svc = PlacesService(_settings(), client=client)

    out = svc.enrich(sample_itinerary)

    act = out.days[0].activities[0]
    assert act.lat is None
    assert act.lng is None


def test_already_geocoded_activity_is_skipped(sample_itinerary):
    sample_itinerary.days[0].activities[0].lat = 10.0
    sample_itinerary.days[0].activities[0].lng = 20.0
    client = MagicMock()
    svc = PlacesService(_settings(), client=client)

    svc.enrich(sample_itinerary)

    client.geocode.assert_not_called()


def test_no_maps_key_is_a_noop(sample_itinerary):
    client = MagicMock()
    svc = PlacesService(_settings(maps_key=""), client=client)

    out = svc.enrich(sample_itinerary)

    assert out is sample_itinerary
    client.geocode.assert_not_called()


def test_geocode_error_is_swallowed(sample_itinerary):
    client = MagicMock()
    client.geocode.side_effect = RuntimeError("maps 500")
    svc = PlacesService(_settings(), client=client)

    # Must not raise — a failed geocode simply leaves coordinates null.
    out = svc.enrich(sample_itinerary)
    assert out.days[0].activities[0].lat is None
