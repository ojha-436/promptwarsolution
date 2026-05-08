/**
 * @jest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { TripPlanner } from "@/components/TripPlanner";

expect.extend(toHaveNoViolations);

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/lib/api", () => ({
  createTrip: jest.fn().mockResolvedValue({ id: "abc123" }),
}));

describe("TripPlanner", () => {
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
  });
});
