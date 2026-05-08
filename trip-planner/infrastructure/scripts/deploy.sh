#!/usr/bin/env bash
# One-command deploy. Re-runnable.
#
# Usage:
#   GCP_PROJECT=my-proj GCP_REGION=asia-south1 ./infrastructure/scripts/deploy.sh
#
set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT}"
: "${GCP_REGION:=asia-south1}"

REPO="wanderly"
echo "==> Project: $GCP_PROJECT  Region: $GCP_REGION"

echo "==> Enabling APIs"
gcloud services enable \
  run.googleapis.com firestore.googleapis.com pubsub.googleapis.com \
  secretmanager.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com iam.googleapis.com \
  generativelanguage.googleapis.com identitytoolkit.googleapis.com \
  --project "$GCP_PROJECT"

echo "==> Creating Artifact Registry repo (idempotent)"
gcloud artifacts repositories create "$REPO" \
  --project "$GCP_PROJECT" --location "$GCP_REGION" \
  --repository-format=docker || true

echo "==> Storing Gemini key in Secret Manager"
if ! gcloud secrets describe gemini-api-key --project "$GCP_PROJECT" >/dev/null 2>&1; then
  read -rsp "Paste GEMINI_API_KEY: " GK; echo
  printf "%s" "$GK" | gcloud secrets create gemini-api-key \
    --project "$GCP_PROJECT" --replication-policy=automatic --data-file=-
fi

echo "==> Submitting Cloud Build (test → build → push → deploy)"
gcloud builds submit \
  --project "$GCP_PROJECT" \
  --config cloudbuild.yaml \
  --substitutions=_REGION="$GCP_REGION",_AR_REPO="$REPO" \
  .

echo "==> Done. Service URLs:"
gcloud run services list --project "$GCP_PROJECT" --region "$GCP_REGION" \
  --format='table(name,uri)'
