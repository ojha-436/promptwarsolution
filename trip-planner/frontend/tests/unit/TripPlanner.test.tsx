/**
 * @jest-environment jsdom
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { TripPlanner } from "@/components/TripPlanner";
import { createTrip } from "@/lib/api";

expect.extend(toHaveNoViolations);

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/lib/api", () => ({
  createTrip: jest.fn().mockResolvedValue({ id: "abc123" }),
}));

const mockCreateTrip = createTrip as jest.MockedFunction<typeof createTrip>;

describe("TripPlanner", () => {
  afterEach(() => jest.clearAllMocks());

  it("renders all required fields", () => {
    render(<TripPlanner />);
    expect(screen.getByLabelText(/destination/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/total budget/i)).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: /travel style/i })).toBeInTheDocument();
  });

  it("has no obvious accessibility violations", async () => {
    const { container } = render(<TripPlanner />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("blocks submission and shows errors when required fields are empty", async () => {
    const user = userEvent.setup();
    render(<TripPlanner />);
    await user.click(screen.getByRole("button", { name: /plan my trip/i }));
    // Validation error appears and focus moves to first invalid field
    expect(screen.getByLabelText(/destination/i)).toHaveFocus();
    expect(mockCreateTrip).not.toHaveBeenCalled();
  });

  it("submits a valid form and navigates to the trip page", async () => {
    const user = userEvent.setup();
    render(<TripPlanner />);

    await user.type(screen.getByLabelText(/destination/i), "Manali");
    fireEvent.change(screen.getByLabelText(/start date/i), { target: { value: "2026-06-01" } });
    fireEvent.change(screen.getByLabelText(/end date/i), { target: { value: "2026-06-04" } });
    fireEvent.change(screen.getByLabelText(/total budget/i), { target: { value: "50000" } });

    await user.click(screen.getByRole("button", { name: /plan my trip/i }));

    await waitFor(() => expect(mockCreateTrip).toHaveBeenCalledTimes(1));
    const submitted = mockCreateTrip.mock.calls[0]![0];
    expect(submitted.destination).toBe("Manali");
    expect(submitted.constraints.budget_total_inr).toBe(50000);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/trip/abc123"));
  });

  it("shows a server error banner when the API call fails", async () => {
    mockCreateTrip.mockRejectedValueOnce(new Error("API 500: down"));
    const user = userEvent.setup();
    render(<TripPlanner />);

    await user.type(screen.getByLabelText(/destination/i), "Goa");
    fireEvent.change(screen.getByLabelText(/start date/i), { target: { value: "2026-06-01" } });
    fireEvent.change(screen.getByLabelText(/end date/i), { target: { value: "2026-06-03" } });
    fireEvent.change(screen.getByLabelText(/total budget/i), { target: { value: "30000" } });

    await user.click(screen.getByRole("button", { name: /plan my trip/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/api 500/i));
  });
});
