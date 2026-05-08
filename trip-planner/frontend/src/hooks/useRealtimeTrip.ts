"use client";

import { doc, onSnapshot } from "firebase/firestore";
import { useEffect, useState } from "react";
import { firebaseAuth, firestore } from "@/lib/firebase";
import type { Trip } from "@/types/trip";

/**
 * Subscribe to /users/{uid}/trips/{tripId} and stream updates straight into
 * React state. This is the magic for "real-time updates" — when the Pub/Sub
 * worker writes a re-planned itinerary to Firestore, this fires automatically.
 */
export function useRealtimeTrip(tripId: string | null): {
  trip: Trip | null;
  loading: boolean;
  error: Error | null;
} {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const uid = firebaseAuth.currentUser?.uid;
    if (!uid || !tripId) {
      setLoading(false);
      return;
    }
    const ref = doc(firestore, "users", uid, "trips", tripId);
    const unsub = onSnapshot(
      ref,
      (snap) => {
        if (snap.exists()) {
          setTrip(snap.data() as Trip);
        }
        setLoading(false);
      },
      (err) => {
        setError(err);
        setLoading(false);
      },
    );
    return () => unsub();
  }, [tripId]);

  return { trip, loading, error };
}
