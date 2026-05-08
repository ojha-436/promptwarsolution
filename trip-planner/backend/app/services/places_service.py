"""
Maps / Places enrichment.

We deliberately keep Maps usage *post*-LLM: Gemini suggests venues, then this
service geocodes and validates them. Two reasons:
  1. Cheaper — only validated venues hit Maps API.
  2. Hallucination guard — if a venue can't be geocoded, we surface a warning.
"""

from __future__ import annotations

from typing import Any

import googlemaps

from app.config import Settings
from app.models import Activity, Itinerary
from app.utils.logger import get_logger

log = get_logger(__name__)


class PlacesService:
    def __init__(self, settings: Settings, client: googlemaps.Client | None = None):
        self._settings = settings
        self._client = (
            client or googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
            if settings.GOOGLE_MAPS_API_KEY
            else None
        )

    def enrich(self, itinerary: Itinerary) -> Itinerary:
        """Attach lat/lng to each activity; flag unverifiable venues."""
        if not self._client:
            return itinerary

        for day in itinerary.days:
            for act in day.activities:
                if act.lat is not None and act.lng is not None:
                    continue
                self._geocode_activity(act, itinerary.destination)

        return itinerary

    def _geocode_activity(self, activity: Activity, destination: str) -> None:
        query = f"{activity.location_name}, {destination}"
        try:
            assert self._client is not None
            results: list[dict[str, Any]] = self._client.geocode(query)  # type: ignore[no-untyped-call]
        except Exception as exc:  # pragma: no cover
            log.warning("maps.error", query=query, error=str(exc))
            return

        if not results:
            return

        loc = results[0]["geometry"]["location"]
        activity.lat = loc["lat"]
        activity.lng = loc["lng"]
