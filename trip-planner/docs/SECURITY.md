# Security

Threat model summary, controls, and how each is exercised in tests.

## Trust boundaries

```
[Untrusted user]  →  [Browser]  →  [API]  →  [Gemini, Firestore, Pub/Sub]
       ▲                ▲             ▲
       │                │             └─ private SA, IAM-scoped, no public ingress
       │                └─ CSP, HSTS, no third-party scripts
       └─ Firebase Auth (Google identity provider)
```

## Authentication & authorization

* Every protected route requires `Authorization: Bearer <Firebase ID token>`.
* Tokens are short-lived (1h), refreshed by the Firebase SDK in the browser.
* Server verifies with `firebase_admin.auth.verify_id_token(check_revoked=True)`.
* Backend Cloud Run service is **not** publicly invokable; only the frontend
  service account has `roles/run.invoker` on it (Terraform `iam_member`).
* Firestore Rules enforce per-user isolation — even a leaked ID token cannot
  read another user's trips at the data layer.

## Input validation

* Pydantic v2 with `extra="forbid"` rejects any unknown field.
* String lengths capped (destination 120, notes 500, lists ≤ 20 items).
* Date logic validated (end ≥ start, ≤ 30 days).
* Budget bounded (1k–10M INR).

## Prompt-injection defences

| Vector | Mitigation |
|---|---|
| Malicious `notes` text trying to alter system behaviour | System prompt is server-side and **never** echoed; structured output schema (`response_schema=Itinerary`) constrains response format; rule #9 in the system prompt explicitly tells the model to treat user data as data. |
| Free-form text in `must_avoid` / `interests` | Item-length and list-size caps; the model receives a fully serialised JSON request, not freeform concatenation. |
| Output trying to embed scripts/HTML | All output is JSON, validated against `Itinerary`; the frontend renders only text and never `dangerouslySetInnerHTML`. |
| Hallucinated booking URLs | Schema allows `booking_url: str | null`; we leave null when the model didn't supply a real URL (system prompt rule #7). |

## Secrets management

* No secrets in code, env files, or images.
* GCP Secret Manager holds `gemini-api-key`; Cloud Run mounts it via
  `value_source.secret_key_ref` (`Terraform`). Rotated via Secret Manager
  versions.
* Service accounts are scoped — backend can write to Firestore and publish
  to Pub/Sub but cannot read other secrets.

## Transport & headers

* HTTPS enforced via Cloud Run.
* HSTS, X-Content-Type-Options, X-Frame-Options DENY, Referrer-Policy
  strict-origin-when-cross-origin, tight CSP (`default-src 'none'` on the
  API which serves only JSON; full CSP on the Next.js app).
* CORS allow-list contains only the deployed frontend URL.

## Rate limiting

* `slowapi` token bucket (default 30/min/IP). Not a substitute for Cloud
  Armor — it's an in-process safety net that survives even if the WAF rule
  is misconfigured.

## Containers

* Distroless-style runtime images.
* Non-root user (UID 1001).
* No package-manager baked into the runtime layer.
* `.dockerignore` excludes tests, env files, and CI metadata.

## OWASP Top 10 mapping

| Risk | Control |
|---|---|
| A01 Broken Access Control | ID-token verification + Firestore Rules + IAM-only backend ingress |
| A02 Cryptographic Failures | TLS via Cloud Run, no plaintext secrets |
| A03 Injection | Pydantic validation; no SQL; structured LLM output |
| A04 Insecure Design | Private backend, public frontend; per-user data partition |
| A05 Security Misconfig | Headers + CSP + Helmet-equivalent middleware; least-priv SAs |
| A06 Vulnerable Components | Pinned deps; CI fails on new vulns (TODO: enable Trivy in cloudbuild) |
| A07 Auth Failures | Firebase Auth; check_revoked=True; no server-side sessions |
| A08 Integrity Failures | Image digests pinned at deploy; signed builds (TODO: Binary Authorization) |
| A09 Logging Failures | Structured JSON logs to Cloud Logging w/ request_id |
| A10 SSRF | API only calls Google APIs via SDKs — no user-supplied URL is ever fetched |

## Tested in `backend/tests/test_security.py`

* Security headers present on every response.
* Request-ID propagates verbatim.
* Oversized destination payload rejected (422).
* `extra="forbid"` rejects polluted bodies.
* 404 messages do not leak resource ownership.

## Open follow-ups (deliberately deferred)

* Binary Authorization on Cloud Run.
* Cloud Armor WAF rules in front of the frontend.
* Pen-test by Google's hackathon judges (you!).
