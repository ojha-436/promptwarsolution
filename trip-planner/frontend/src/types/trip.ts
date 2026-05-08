/**
 * Mirrors the backend Pydantic schemas. Hand-kept in sync (no codegen step
 * needed for this MVP — the backend test suite checks the contract).
 */

export type TravelStyle = "budget" | "balanced" | "luxury";
export type Pace = "relaxed" | "moderate" | "packed";
export type DietaryNeed =
  | "vegetarian"
  | "vegan"
  | "halal"
  | "kosher"
  | "gluten_free"
  | "nut_free";
export type MobilityNeed = "none" | "wheelchair" | "limited_walking";
export type TripStatus = "draft" | "planning" | "ready" | "updating" | "failed";
export type ActivityCategory =
  | "food"
  | "sightseeing"
  | "transit"
  | "rest"
  | "shopping"
  | "activity"
  | "lodging";

export interface Preferences {
  style: TravelStyle;
  pace: Pace;
  interests: string[];
  dietary: DietaryNeed[];
  languages: string[];
}

export interface Constraints {
  budget_total_inr: number;
  max_daily_walking_km: number;
  must_include: string[];
  must_avoid: string[];
  accessibility: MobilityNeed;
}

export interface TripRequest {
  destination: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;
  travelers: number;
  preferences: Preferences;
  constraints: Constraints;
  notes: string;
}

export interface Activity {
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  location_name: string;
  lat: number | null;
  lng: number | null;
  estimated_cost_inr: number;
  category: ActivityCategory;
  booking_url: string | null;
  accessibility_notes: string;
}

export interface DayPlan {
  day_index: number;
  date: string;
  summary: string;
  activities: Activity[];
  daily_walking_km: number;
  daily_cost_inr: number;
}

export interface Itinerary {
  destination: string;
  start_date: string;
  end_date: string;
  days: DayPlan[];
  total_cost_inr: number;
  summary: string;
  warnings: string[];
}

export interface Trip {
  id: string;
  user_id: string;
  status: TripStatus;
  request: TripRequest;
  itinerary: Itinerary | null;
  created_at: string;
  updated_at: string;
  version: number;
}
