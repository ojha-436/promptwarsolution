"use client";

import { useEffect, useRef } from "react";
import { useRealtimeTrip } from "@/hooks/useRealtimeTrip";
import { useA11yAnnounce } from "@/hooks/useA11yAnnounce";
import type { Activity, DayPlan } from "@/types/trip";

interface Props {
  tripId: string;
}

export function ItineraryView({ tripId }: Props): JSX.Element {
  const { trip, loading, error } = useRealtimeTrip(tripId);
  const { announce, LiveRegion } = useA11yAnnounce();
  const lastVersion = useRef<number | null>(null);

  // Announce real-time updates to assistive tech.
  useEffect(() => {
    if (!trip) return;
    if (lastVersion.current !== null && trip.version > lastVersion.current) {
      announce(`Itinerary updated to version ${trip.version}.`);
    }
    lastVersion.current = trip.version;
  }, [trip, announce]);

  if (loading) {
    return (
      <p role="status" aria-live="polite">
        Loading your trip…
      </p>
    );
  }
  if (error) {
    return (
      <p role="alert" className="text-danger">
        Could not load this trip: {error.message}
      </p>
    );
  }
  if (!trip) {
    return <p role="status">Trip not found.</p>;
  }

  return (
    <article aria-labelledby="itinerary-heading">
      <LiveRegion />

      <h3 id="itinerary-heading" className="text-xl font-semibold">
        {trip.request.destination}{" "}
        <span className="font-normal text-muted">
          · {trip.request.start_date} → {trip.request.end_date}
        </span>
      </h3>

      <StatusPill status={trip.status} />

      {trip.itinerary && (
        <>
          <p className="mt-4 max-w-2xl">{trip.itinerary.summary}</p>

          {trip.itinerary.warnings.length > 0 && (
            <aside aria-label="Warnings" className="mt-4 rounded border border-warn bg-amber-50 p-3">
              <h4 className="font-semibold text-warn">Heads-up</h4>
              <ul className="list-disc pl-5 text-sm">
                {trip.itinerary.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </aside>
          )}

          <ol className="mt-6 space-y-6" aria-label="Day-by-day plan">
            {trip.itinerary.days.map((d) => (
              <DayCard key={d.day_index} day={d} />
            ))}
          </ol>

          <p className="mt-6 text-sm text-muted">
            Estimated total cost:{" "}
            <strong className="text-ink">
              ₹{trip.itinerary.total_cost_inr.toLocaleString("en-IN")}
            </strong>{" "}
            of ₹{trip.request.constraints.budget_total_inr.toLocaleString("en-IN")} budget.
          </p>
        </>
      )}
    </article>
  );
}

function StatusPill({ status }: { status: string }): JSX.Element {
  const tone =
    status === "ready"
      ? "bg-green-100 text-success"
      : status === "failed"
        ? "bg-red-100 text-danger"
        : "bg-slate-100 text-muted";
  return (
    <span
      role="status"
      aria-label={`Trip status: ${status}`}
      className={`mt-2 inline-block rounded px-2 py-0.5 text-xs font-medium ${tone}`}
    >
      {status}
    </span>
  );
}

function DayCard({ day }: { day: DayPlan }): JSX.Element {
  return (
    <li className="rounded border border-slate-200 p-4">
      <h4 className="font-semibold">
        Day {day.day_index} · {day.date}
      </h4>
      <p className="text-muted">{day.summary}</p>
      <ul className="mt-3 space-y-3">
        {day.activities.map((a, i) => (
          <ActivityRow key={`${day.day_index}-${i}`} a={a} />
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted">
        Walking ~{day.daily_walking_km} km · Day cost ₹
        {day.daily_cost_inr.toLocaleString("en-IN")}
      </p>
    </li>
  );
}

function ActivityRow({ a }: { a: Activity }): JSX.Element {
  return (
    <li className="border-l-4 border-accent pl-3">
      <p>
        <span className="font-medium">
          {a.start_time}–{a.end_time}
        </span>{" "}
        · <span>{a.title}</span>
      </p>
      <p className="text-sm text-muted">{a.description}</p>
      <p className="text-xs text-muted">
        {a.location_name} · ₹{a.estimated_cost_inr.toLocaleString("en-IN")}
        {a.accessibility_notes && (
          <>
            {" · "}
            <span className="italic">{a.accessibility_notes}</span>
          </>
        )}
      </p>
    </li>
  );
}
