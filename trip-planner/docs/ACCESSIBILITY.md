# Accessibility

Targeting **WCAG 2.1 AA**. Tested with axe-core in unit tests (`jest-axe`)
and end-to-end (`@axe-core/playwright`).

## Perceivable

* Semantic landmarks (`<header>`, `<main>`, `<nav>`, `<footer>`) on every page.
* All form fields have a programmatic `<label htmlFor>` association.
* Color contrast: every Tailwind token used for text vs. background passes
  4.5:1; `accent` (#1d4ed8) on white = 7.6:1, `muted` (#475569) on white =
  7.0:1.
* Decorative emoji marked `aria-hidden`; informative icons have `aria-label`.

## Operable

* All interactive elements reachable by `Tab`; visible focus ring (3px solid
  blue, never removed).
* Skip-link as the first focusable element jumps to `#main`.
* No keyboard traps. Forms can be fully completed without a mouse — verified
  in `tests/e2e/plan.spec.ts`.
* Targets ≥ 24×24 CSS px (Tailwind buttons use `py-2.5 px-5`).

## Understandable

* Plain-English labels and error messages.
* Errors associated with fields via `aria-invalid` + `aria-describedby`.
* On submit failure, focus moves to the first invalid field so screen-reader
  users hear the error immediately.
* Language declared (`<html lang="en">`).

## Robust

* All custom widgets use Radix UI primitives (built-in ARIA).
* Live region for real-time updates (`useA11yAnnounce`) announces version
  changes politely without stealing focus.
* Reduced-motion media query nullifies animation durations.

## CI gates

* `tests/unit/TripPlanner.test.tsx` runs `axe()` on the form — zero
  violations required.
* `tests/e2e/plan.spec.ts` runs Playwright + AxeBuilder against
  `wcag21aa, wcag22aa` tags.
