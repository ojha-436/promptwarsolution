"""
Firestore data access for trips.

Schema:
    /users/{uid}/trips/{tripId}    document = Trip (Pydantic dump)

Why per-user subcollections: row-level security via Firestore Rules is dead
simple — `request.auth.uid == userId` is enough to isolate tenants.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud import firestore

from app.models import Trip, TripStatus
from app.utils.logger import get_logger

log = get_logger(__name__)


class FirestoreService:
    def __init__(self, client: firestore.Client | None = None):
        self._client = client or firestore.Client()

    def _doc_ref(self, user_id: str, trip_id: str) -> firestore.DocumentReference:
        return (
            self._client.collection("users")
            .document(user_id)
            .collection("trips")
            .document(trip_id)
        )

    def save(self, trip: Trip) -> None:
        """Persist the full trip document (create or overwrite)."""
        log.info("firestore.save", trip_id=trip.id, user_id=trip.user_id, status=trip.status)
        self._doc_ref(trip.user_id, trip.id).set(trip.model_dump(mode="json"))

    def get(self, user_id: str, trip_id: str) -> Trip | None:
        """Return the stored trip, or None if it does not exist for this user."""
        snap = self._doc_ref(user_id, trip_id).get()
        if not snap.exists:
            return None
        return Trip.model_validate(snap.to_dict() or {})

    def update_status(
        self, user_id: str, trip_id: str, status: TripStatus
    ) -> None:
        """Patch only the status + updated_at fields (cheaper than a full write)."""
        self._doc_ref(user_id, trip_id).update(
            {
                "status": status.value,
                "updated_at": datetime.now(tz=UTC).isoformat(),
            }
        )

    def list_for_user(self, user_id: str, limit: int = 50) -> list[Trip]:
        """Return the user's trips, newest first, capped at ``limit``."""
        snaps = (
            self._client.collection("users")
            .document(user_id)
            .collection("trips")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [Trip.model_validate(s.to_dict() or {}) for s in snaps]
