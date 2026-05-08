import { TripPlanner } from "@/components/TripPlanner";

export default function HomePage() {
  return (
    <>
      <h2 className="text-2xl font-semibold mb-2">Plan a trip</h2>
      <p className="text-muted mb-8 max-w-2xl">
        Tell us where you&rsquo;re going, your preferences, and any
        constraints. We&rsquo;ll build a day-by-day plan and update it live as
        conditions change.
      </p>
      <TripPlanner />
    </>
  );
}
