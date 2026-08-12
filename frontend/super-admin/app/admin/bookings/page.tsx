/**
 * Compatibility entry point for the retired generic booking list.
 * Home Services bookings and their resulting jobs are managed together in
 * the canonical operational workspace.  Keeping this redirect prevents old
 * bookmarks and admin search results from landing on a 404.
 */
import { redirect } from "next/navigation";

export default function LegacyBookingsRedirect() {
  redirect("/admin/home-services/bookings-jobs");
}
