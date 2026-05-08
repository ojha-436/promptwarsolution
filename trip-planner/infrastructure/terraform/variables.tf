variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  default     = "asia-south1"
  description = "Cloud Run region"
}

variable "backend_image" {
  type        = string
  description = "Full image URL for the backend (set by Cloud Build)"
}

variable "frontend_image" {
  type        = string
  description = "Full image URL for the frontend (set by Cloud Build)"
}

variable "frontend_url" {
  type        = string
  default     = "https://wanderly.example.com"
  description = "Public URL of the frontend; used for CORS allow-list"
}
