import { redirect } from "next/navigation";

// Consolidated into /jobs ("Bookings & Jobs") -- the provider no longer
// needs a separate destination for the booking-confirmation stage of the
// pipeline; it's one row type in the same unified table as jobs.
export default function BookingsPage() {
  redirect("/jobs");
}
