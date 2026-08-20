import { redirect } from "next/navigation";

// Compatibility-only route. A server redirect avoids shipping a retired
// client page and prevents the blank flash the old useEffect redirect caused.
export default function LegacyOperationsRedirect() {
  redirect("/admin/home-services/bookings-jobs");
}
