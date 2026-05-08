###############################################################################
# Wanderly — full GCP environment in one apply.                               #
#                                                                             #
# Creates:                                                                    #
#   * Service accounts for backend & frontend (least privilege)               #
#   * Firestore Native database                                               #
#   * Pub/Sub topic + subscription for trip-events                            #
#   * Secret Manager bindings (gemini-api-key, maps-api-key)                  #
#   * Cloud Run services (backend + frontend)                                 #
#   * Public ingress with IAM-anonymous invoker for the frontend only         #
#                                                                             #
# Backend is invoked from the frontend's SSR layer using ID-token             #
# audience binding — no public anonymous access to the API.                   #
###############################################################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.40" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── APIs ──────────────────────────────────────────────────────────────────

locals {
  required_apis = [
    "run.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "maps-backend.googleapis.com",
    "places-backend.googleapis.com",
    "identitytoolkit.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.required_apis)
  service            = each.value
  disable_on_destroy = false
}

# ── Service accounts ──────────────────────────────────────────────────────

resource "google_service_account" "backend" {
  account_id   = "wanderly-backend"
  display_name = "Wanderly Backend (Cloud Run)"
}

resource "google_service_account" "frontend" {
  account_id   = "wanderly-frontend"
  display_name = "Wanderly Frontend (Cloud Run)"
}

# Backend permissions: Firestore RW, Pub/Sub publish, Secret access, Logs write
resource "google_project_iam_member" "backend_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}
resource "google_project_iam_member" "backend_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.backend.email}"
}
resource "google_project_iam_member" "backend_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# ── Firestore (Native mode) ───────────────────────────────────────────────

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# ── Pub/Sub: live trip events ─────────────────────────────────────────────

resource "google_pubsub_topic" "trip_events" {
  name       = "trip-events"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "trip_events_replan" {
  name  = "trip-events-replan"
  topic = google_pubsub_topic.trip_events.name

  ack_deadline_seconds = 60
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# ── Secrets ──────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "gemini-api-key"
  replication { auto {} }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "backend_gemini" {
  secret_id = google_secret_manager_secret.gemini_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# ── Cloud Run: backend ───────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "wanderly-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.backend.email
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.backend_image
      ports { container_port = 8080 }

      env { name = "ENV" value = "prod" }
      env { name = "GCP_PROJECT" value = var.project_id }
      env { name = "GCP_REGION" value = var.region }
      env { name = "FIREBASE_PROJECT_ID" value = var.project_id }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
      env { name = "CORS_ORIGINS" value = jsonencode([var.frontend_url]) }

      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 3
      }
      liveness_probe {
        http_get { path = "/health" }
        period_seconds = 30
      }
    }
  }
  depends_on = [google_project_service.apis]
}

# Lock down: only the frontend SA can invoke the backend
resource "google_cloud_run_v2_service_iam_member" "backend_invoker_frontend" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend.email}"
}

# ── Cloud Run: frontend ──────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "wanderly-web"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.frontend.email
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.frontend_image
      ports { container_port = 3000 }
      env { name = "NEXT_PUBLIC_API_BASE" value = google_cloud_run_v2_service.backend.uri }
      env { name = "NEXT_PUBLIC_FIREBASE_PROJECT_ID" value = var.project_id }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
    }
  }
  depends_on = [google_project_service.apis]
}

# Public access to the web app (still gated behind Firebase Auth in-app)
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = google_cloud_run_v2_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
