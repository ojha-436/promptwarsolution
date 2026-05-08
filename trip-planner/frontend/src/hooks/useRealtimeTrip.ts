"use client";

import { useEffect, useState } from "react";
import { getTrip } from "@/lib/api";
import type { Trip } from "@/types/trip";

/**
 * Poll the backend API for updates since Firebase Client Auth is disabled.
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
    if (!tripId) {
      setLoading(false);
      return;
    }

    let mounted = true;
    const fetchTrip = async () => {
      try {
        const data = await getTrip(tripId);
        if (mounted) {
          setTrip(data);
          setLoading(false);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      }
    };

    fetchTrip();
    const intervalId = setInterval(fetchTrip, 3000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [tripId]);

  return { trip, loading, error };
}
