/**
 * @jest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { ItineraryView } from "@/components/ItineraryView";
import { useRealtimeTrip } from "@/hooks/useRealtimeTrip";
import type { Trip } from "@/types/trip";

jest.mock("@/hooks/useRealtimeTrip", () => ({ useRealtimeTrip: jest.fn() }));

const mockHook = useRealtimeTrip as jest.MockedFunction<typeof useRealtimeTrip>;

const READY_TRIP: Trip = {
  id: "t1",
  user_id: "u1",
  status: "ready",
  version: 1,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  request: {
    destination: "Manali",
    start_date: "2026-06-01",
    end_date: "2026-06-02",
    travelers: 2,
    preferences: { style: "balanced", pace: "moderate", interests: [], dietary: [], languages: ["en"] },
    constraints: {
      budget_total_inr: 50000,
      max_daily_walking_km: 8,
      must_include: [],
      must_avoid: [],
      accessibility: "none",
    },
    notes: "",
  },
  itinerary: {
    destination: "Manali",
    start_date: "2026-06-01",
    end_date: "2026-06-02",
    total_cost_inr: 3000,
    summary: "A short trip.",
    warnings: ["Rain expected on Day 1"],
    days: [
      {
        day_index: 1,
        date: "2026-06-01",
        summary: "Arrival",
        daily_walking_km: 1,
        daily_cost_inr: 3000,
        activities: [
          {
            title: "Check in",
            description: "Hotel check-in",
            start_time: "14:00",
            end_time: "15:00",
            location_name: "Hotel",
            lat: null,
            lng: null,
            estimated_cost_inr: 3000,
            category: "lodging",
            booking_url: null,
            accessibility_notes: "",
          },
        ],
      },
    ],
  },
};

describe("ItineraryView", () => {
  afterEach(() => jest.clearAllMocks());

  it("shows a loading state", () => {
    mockHook.mockReturnValue({ trip: null, loading: true, error: null });
    render(<ItineraryView tripId="t1" />);
    expect(screen.getByText(/loading your trip/i)).toBeInTheDocument();
  });

  it("shows an error state", () => {
    mockHook.mockReturnValue({ trip: null, loading: false, error: new Error("nope") });
    render(<ItineraryView tripId="t1" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/nope/i);
  });

  it("renders the itinerary, day plan, and warnings", () => {
    mockHook.mockReturnValue({ trip: READY_TRIP, loading: false, error: null });
    render(<ItineraryView tripId="t1" />);

    expect(screen.getByRole("heading", { name: /manali/i })).toBeInTheDocument();
    expect(screen.getByText(/heads-up/i)).toBeInTheDocument();
    expect(screen.getByText(/rain expected on day 1/i)).toBeInTheDocument();
    expect(screen.getByText(/check in/i)).toBeInTheDocument();
    expect(screen.getByText(/a short trip/i)).toBeInTheDocument();
  });
});
