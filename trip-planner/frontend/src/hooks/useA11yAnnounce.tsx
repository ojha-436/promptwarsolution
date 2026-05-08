"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * Announce a message to screen readers via an aria-live region.
 *
 * Usage:
 *   const { announce, LiveRegion } = useA11yAnnounce();
 *   announce("Itinerary updated due to rain forecast");
 *   <LiveRegion />
 */
export function useA11yAnnounce(): {
  announce: (msg: string) => void;
  LiveRegion: () => JSX.Element;
} {
  const ref = useRef<HTMLDivElement | null>(null);

  const announce = useCallback((msg: string) => {
    if (!ref.current) return;
    // Clear first so identical consecutive messages still get announced.
    ref.current.textContent = "";
    setTimeout(() => {
      if (ref.current) ref.current.textContent = msg;
    }, 50);
  }, []);

  // Cleanup
  useEffect(() => () => { if (ref.current) ref.current.textContent = ""; }, []);

  const LiveRegion = () => (
    <div
      ref={ref}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  );

  return { announce, LiveRegion };
}
