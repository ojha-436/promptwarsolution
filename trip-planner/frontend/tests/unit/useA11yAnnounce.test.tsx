/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useA11yAnnounce } from "@/hooks/useA11yAnnounce";

function Harness(): JSX.Element {
  const { announce, LiveRegion } = useA11yAnnounce();
  return (
    <>
      <button type="button" onClick={() => announce("Itinerary updated")}>
        announce
      </button>
      <LiveRegion />
    </>
  );
}

describe("useA11yAnnounce", () => {
  it("renders a polite, atomic live region", () => {
    render(<Harness />);
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveAttribute("aria-atomic", "true");
  });

  it("writes the announced message into the live region", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: /announce/i }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Itinerary updated"),
    );
  });
});
