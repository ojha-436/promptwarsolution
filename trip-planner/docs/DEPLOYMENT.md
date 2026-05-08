# Deployment

End-to-end deploy to GCP. Tested on a fresh project — start to finish in
~12 minutes.

## Prerequisites

* `gcloud` CLI authenticated to the target project, billing enabled.
* `terraform` ≥ 1.6.
* `node` ≥ 20 and `python` ≥ 3.12 (only for local dev / running tests).
* Firebase project (same project ID) with Email/Google sign-in enabled in
  the Firebase Console.
* A Gemini API key (from https://ai.google.dev/).

## 1 — One-shot script

```bash
export GCP_PROJECT="my-wanderly"
export GCP_REGION="asia-south1"
./infrastructure/scripts/deploy.sh
```

The script:

1. Enables APIs.
2. Creates the Artifact Registry repo if missing.
3. Stores the Gemini key in Secret Manager (prompts once, not stored on disk).
4. Submits Cloud Build → tests → builds → pushes → deploys both services.

## 2 — Apply Terraform (recommended for prod)

After the first build has produced images, switch to the Terraform-managed
deploy so all resources are tracked:

```bash
cd infrastructure/terraform
terraform init
terraform apply \
  -var="project_id=$GCP_PROJECT" \
  -var="region=$GCP_REGION" \
  -var="backend_image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/wanderly/api:latest" \
  -var="frontend_image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/wanderly/web:latest"
```

Outputs include `backend_url` and `frontend_url`.

## 3 — Apply Firestore rules

```bash
gcloud firestore databases create --location=$GCP_REGION --type=firestore-native || true
gcloud firebase deploy --only firestore:rules \
  --project $GCP_PROJECT --rules-file infrastructure/firestore.rules
```

## 4 — Configure the frontend at runtime

Set these as env vars on the `wanderly-web` Cloud Run service:

```
NEXT_PUBLIC_API_BASE         (output: backend_url)
NEXT_PUBLIC_FIREBASE_API_KEY (Firebase console → web app config)
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_PROJECT_ID
```

## 5 — Sanity check

```bash
curl -fsS "$BACKEND_URL/health"
# {"status":"ok"}

# Open the frontend URL in a browser, sign in, plan a trip.
```

## Cost estimate (back-of-envelope)

| Service | Free tier | Beyond |
|---|---|---|
| Cloud Run | 2M req/mo, 360k GB-s | $0.00002400/request after |
| Firestore | 50k reads, 20k writes/day | small |
| Gemini 1.5 Pro | quota-bound | $1.25/M input tokens (planning ≈ 4k tokens) |
| Pub/Sub | 10 GB/mo | ~$0.05/GB |
| Cloud Build | 120 build-min/day | $0.003/build-min |

A demo with 1k trip plans/month is well inside free tier on everything except
Gemini, which would run roughly $5–10.
