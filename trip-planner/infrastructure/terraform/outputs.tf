output "backend_url" {
  value       = google_cloud_run_v2_service.backend.uri
  description = "Cloud Run URL of the backend"
}

output "frontend_url" {
  value       = google_cloud_run_v2_service.frontend.uri
  description = "Cloud Run URL of the frontend"
}

output "pubsub_topic" {
  value = google_pubsub_topic.trip_events.id
}
