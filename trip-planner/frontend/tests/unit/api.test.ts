/**
 * @jest-environment jsdom
 */
import { createTrip, getTrip, pushEvent } from "@/lib/api";
import type { TripRequest } from "@/types/trip";

jest.mock("@/lib/firebase", () => ({
  firebaseAuth: {
    currentUser: { getIdToken: jest.fn().mockResolvedValue("tok-123") },
  },
}));

const REQUEST = {} as TripRequest;

describe("api client", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  it("attaches the Firebase bearer token and JSON content-type", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "t1" }) });
    global.fetch = fetchMock as unknown as typeof fetch;

    const trip = await createTrip(REQUEST);

    expect(trip).toEqual({ id: "t1" });
    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok-123");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("throws with status and detail on a non-2xx response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "internal error",
    }) as unknown as typeof fetch;

    await expect(getTrip("x")).rejects.toThrow("API 500: internal error");
  });

  it("posts an event body with type and payload", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ message_id: "m1" }) });
    global.fetch = fetchMock as unknown as typeof fetch;

    const res = await pushEvent("t1", "weather", { day: 2 });

    expect(res).toEqual({ message_id: "m1" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/v1/trips/t1/events");
    expect(JSON.parse(init.body)).toEqual({ type: "weather", payload: { day: 2 } });
  });
});
