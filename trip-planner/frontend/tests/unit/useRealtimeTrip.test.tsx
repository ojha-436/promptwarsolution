/**
 * @jest-environment jsdom
 */
import { renderHook, waitFor } from "@testing-library/react";
import { useRealtimeTrip } from "@/hooks/useRealtimeTrip";
import { getTrip } from "@/lib/api";

jest.mock("@/lib/api", () => ({ getTrip: jest.fn() }));

const mockGetTrip = getTrip as jest.MockedFunction<typeof getTrip>;

describe("useRealtimeTrip", () => {
  afterEach(() => jest.clearAllMocks());

  it("loads a trip and clears the loading flag", async () => {
    mockGetTrip.mockResolvedValue({ id: "t1", version: 1 } as never);
    const { result } = renderHook(() => useRealtimeTrip("t1"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.trip).toEqual({ id: "t1", version: 1 });
    expect(result.current.error).toBeNull();
  });

  it("surfaces an error when the fetch fails", async () => {
    mockGetTrip.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useRealtimeTrip("t1"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.message).toBe("boom");
  });

  it("is inert when tripId is null", async () => {
    const { result } = renderHook(() => useRealtimeTrip(null));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockGetTrip).not.toHaveBeenCalled();
  });

  it("clears its polling interval on unmount", async () => {
    mockGetTrip.mockResolvedValue({ id: "t1", version: 1 } as never);
    const clearSpy = jest.spyOn(global, "clearInterval");
    const { unmount } = renderHook(() => useRealtimeTrip("t1"));
    unmount();
    expect(clearSpy).toHaveBeenCalled();
    clearSpy.mockRestore();
  });
});
