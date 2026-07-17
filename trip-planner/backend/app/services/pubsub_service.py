"""
Pub/Sub publisher for trip-events.

Live conditions (weather, flight, closure) are written by:
  * Cloud Scheduler jobs (weather pull every 30 min)
  * Webhooks from upstream APIs (flight provider)
  * Cron functions (POI-closure scraping)
to the `trip-events` topic. A single Cloud Function subscriber consumes the
topic, calls `GeminiService.repair_itinerary`, and writes the new plan to
Firestore — which streams to the user's browser via onSnapshot.
"""

from __future__ import annotations

from google.cloud import pubsub_v1

from app.config import Settings
from app.models import TripEvent
from app.utils.logger import get_logger

log = get_logger(__name__)


class PubSubService:
    def __init__(self, settings: Settings, publisher: pubsub_v1.PublisherClient | None = None):
        self._settings = settings
        self._publisher = publisher or pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(
            settings.GCP_PROJECT, settings.PUBSUB_TRIP_EVENTS_TOPIC
        )

    def publish_event(self, event: TripEvent) -> str:
        """Publish a TripEvent. Returns the message_id."""
        data = event.model_dump_json().encode("utf-8")
        future = self._publisher.publish(
            self._topic_path,
            data,
            trip_id=event.trip_id,
            event_type=event.type.value,
        )
        msg_id: str = future.result(timeout=10)
        log.info("pubsub.published", trip_id=event.trip_id, type=event.type.value, msg_id=msg_id)
        return msg_id
