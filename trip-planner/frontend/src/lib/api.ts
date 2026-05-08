/**
 * Tiny typed fetch wrapper. Always sends the Firebase ID token; throws on
 * non-2xx; returns parsed JSON.
 */
import type { Trip, TripRequest } from "@/types/trip";
import { firebaseAuth } from "./firebase";

const API_BASE = "/api";

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const user = firebaseAuth.currentUser;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (user) {
    const token = await user.getIdToken();
    headers.set("Authorization", `Bearer ${token}`);
  }
  const r = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`API ${r.status}: ${detail}`);
  }
  return r;
}

export async function createTrip(req: TripRequest): Promise<Trip> {
  const r = await authedFetch("/v1/trips", { method: "POST", body: JSON.stringify(req) });
  return r.json();
}

export async function listTrips(): Promise<Trip[]> {
  const r = await authedFetch("/v1/trips");
  return r.json();
}

export async function getTrip(id: string): Promise<Trip> {
  const r = await authedFetch(`/v1/trips/${id}`);
  return r.json();
}

export async function pushEvent(
  id: string,
  type: string,
  payload: Record<string, unknown>,
): Promise<{ message_id: string }> {
  const r = await authedFetch(`/v1/trips/${id}/events`, {
    method: "POST",
    body: JSON.stringify({ type, payload }),
  });
  return r.json();
}
