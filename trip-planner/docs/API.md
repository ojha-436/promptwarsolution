# API reference

All endpoints versioned under `/v1`. JSON in, JSON out. Auth via
`Authorization: Bearer <Firebase ID token>` (except `/health`).

## `POST /v1/trips`

Create a new trip plan.

**Body**

```json
{
  "destination": "Manali",
  "start_date": "2026-06-01",
  "end_date": "2026-06-04",
  "travelers": 2,
  "preferences": {
    "style": "balanced",
    "pace": "moderate",
    "interests": ["nature", "food"],
    "dietary": ["vegetarian"],
    "languages": ["en"]
  },
  "constraints": {
    "budget_total_inr": 50000,
    "max_daily_walking_km": 8,
    "must_include": [],
    "must_avoid": [],
    "accessibility": "none"
  },
  "notes": "Prefer mornings"
}
```

**Response — 202 Accepted**

```json
{
  "id": "8f3a...",
  "user_id": "uid_xyz",
  "status": "planning",
  "request": { "...": "echoed back" },
  "itinerary": null,
  "created_at": "2026-05-08T10:00:00Z",
  "updated_at": "2026-05-08T10:00:00Z",
  "version": 1
}
```

The client should subscribe to `/users/{uid}/trips/{id}` in Firestore for the
final `READY` (with `itinerary`) or `FAILED` state.

## `GET /v1/trips/{id}`

Fetch a single trip. **404** if not owned by the caller.

## `GET /v1/trips`

List the caller's trips, newest first.

## `POST /v1/trips/{id}/events`

Inject a real-time event. Sets the trip to `UPDATING`, publishes a
`TripEvent` to `trip-events` topic; a Cloud Function calls
`GeminiService.repair_itinerary` and writes the new plan to Firestore.

**Body**

```json
{
  "type": "weather",
  "payload": { "day": 2, "condition": "rain", "severity": "high" }
}
```

`type` ∈ `weather | flight_delay | closure | user_edit`.

## `GET /health`

`{ "status": "ok" }` — Cloud Run liveness probe.

## Error format

All errors follow FastAPI's default:

```json
{ "detail": "human-readable reason" }
```

* 400 / 422 — validation
* 401 — missing/invalid token
* 404 — trip not owned by caller (also when not found, to avoid enumeration)
* 429 — rate limited
* 5xx — internal; retry with exponential backoff
