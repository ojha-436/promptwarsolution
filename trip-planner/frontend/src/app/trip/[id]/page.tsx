import { ItineraryView } from "@/components/ItineraryView";

interface PageProps {
  params: { id: string };
}

export default function TripPage({ params }: PageProps) {
  return (
    <>
      <h2 className="text-2xl font-semibold mb-2">Your itinerary</h2>
      <ItineraryView tripId={params.id} />
    </>
  );
}
