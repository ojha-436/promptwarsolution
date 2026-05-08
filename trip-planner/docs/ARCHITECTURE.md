# Architecture

Wanderly is a serverless, event-driven app designed to score well on the
problem statement (*Plan trips dynamically with preferences, constraints,
and real-time updates*) by separating three concerns cleanly:

1. **Generation** — turning intent into a plan (Gemini, structured output).
2. **Persistence and streaming** — Firestore as both store and live channel.
3. **Re-planning** — Pub/Sub fan-in for any external signal that should
   change the plan (weather, flight, closures, user edits).

## Component diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Browser (Next.js SSR + CSR)                  │
│  Sign in (Firebase Auth)  Form (a11y)  ItineraryView (Firestore stream) │
└───────────────┬───────────────────────────────────┬──────────────────────┘
                │ ID-token                          │ onSnapshot
                ▼                                   ▼
        ┌────────────────────┐            ┌──────────────────────┐
        │ FastAPI (Cloud Run)│            │ Firestore (Native)   │
        │  /v1/trips         │◀───────────│  /users/{u}/trips/{t}│
        │  /v1/.../events    │  read/write│                      │
        └─┬────────┬─────────┘            └──────────────────────┘
          │        │                                ▲
          │        │ publish                        │ write
          │        ▼                                │
          │   ┌──────────┐                  ┌────────────┐
          │   │ Pub/Sub  │ ─────────────────►│ Cloud Fn   │
          │   │ topic    │ pull subscription │ replan     │
          │   └──────────┘                  └─┬──────────┘
          │                                   │
          ▼                                   ▼
   ┌────────────┐                       ┌────────────┐
   │ Gemini API │                       │ Gemini API │ (repair)
   └────────────┘                       └────────────┘
          ▲
          │ enrich
   ┌────────────┐
   │ Maps API   │
   └────────────┘
```

## Request lifecycle: creating a trip

1. User signs in via Firebase Auth (Google identity).
2. Browser POSTs `/v1/trips` with the validated form payload + ID token.
3. FastAPI:
   - verifies ID token (`firebase_admin.auth.verify_id_token`),
   - validates payload (Pydantic v2, `extra="forbid"` blocks extra fields),
   - writes a `PLANNING` Trip doc to Firestore,
   - schedules background work, returns 202.
4. Background task calls `GeminiService.generate_itinerary` with structured
   output (`response_schema=Itinerary`).
5. Maps geocodes each suggested venue and flags hallucinations.
6. The doc is updated to `READY` in Firestore.
7. The browser, already subscribed via `onSnapshot`, renders the plan.

## Request lifecycle: real-time update

1. A Cloud Scheduler job fires every 30 minutes, querying weather for any
   trip currently within its travel window.
2. If conditions change materially, it POSTs to
   `/v1/trips/{id}/events` with `{ "type": "weather", "payload": ... }`.
3. The API publishes a `TripEvent` to the `trip-events` topic.
4. A Cloud Function subscribed to the topic calls
   `GeminiService.repair_itinerary` with the live event as context, writes
   the new plan back to Firestore.
5. The browser sees a Firestore update; `useRealtimeTrip` re-renders the
   itinerary; `useA11yAnnounce` fires an `aria-live="polite"` announcement so
   screen-reader users hear the change.

## Why this composition

* **Cloud Run** keeps everything stateless, autoscaling to zero, paying only
  per request — fits a hackathon budget and a real product alike.
* **Firestore** is both the system of record and the WebSocket-equivalent
  for live UI. No bespoke realtime layer needed.
* **Pub/Sub** decouples re-plan triggers from their origin (weather cron,
  flight webhook, user edit), keeping `repair_itinerary` simple and
  uniformly retryable.
* **Structured output via response_schema** is the most reliable way to keep
  Gemini producing parseable, schema-conformant JSON — and is a strong
  prompt-injection defence (the schema cannot be subverted by free-text in
  user `notes`).

## Failure modes

| Failure | Detection | Recovery |
|---|---|---|
| Gemini timeout / 5xx | `tenacity` retries (3 attempts, exp backoff) | After exhaustion, mark Trip `FAILED`; user can retry. |
| Schema mismatch | Pydantic `ValidationError` on parse | Same as above; logged with truncated preview for forensics. |
| Firestore write fails | Exception in router | Caller surfaces 5xx; trip remains `PLANNING` until retry. |
| Pub/Sub publish fails | 10-second blocking ack | API responds 5xx; client retries the event endpoint. |
| Token revoked mid-session | `verify_id_token(check_revoked=True)` | 401 returned; user re-authenticates. |

## Performance budget

* Median end-to-end planning: < 10s for a 5-day trip on `gemini-1.5-pro`.
* Cold-start budget: < 1.5s on Cloud Run with 512 MiB.
* Firestore read latency for `useRealtimeTrip`: < 200ms inside region.
