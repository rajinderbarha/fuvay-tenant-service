import { redirect } from "next/navigation";

/**
 * Compatibility route for old bookmarks. Booking drafts are now the
 * Requests view of the canonical Bookings & Jobs workspace, where a draft
 * becomes a job without appearing twice in admin operations.
 */
export default function BookingDraftsCompatibilityRoute() {
  redirect("/admin/home-services/bookings-jobs?view=requests");
}
