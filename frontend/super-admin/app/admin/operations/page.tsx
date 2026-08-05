/**
 * FINAL-L5-05E — legacy Field Ops Jobs list, superseded first by
 * /admin/home-services/service-jobs (now itself removed 2026-08-04, at
 * explicit user request, in favor of the unified Bookings & Jobs workspace)
 * and now by /admin/home-services/bookings-jobs. This route is a
 * compatibility redirect only. The old `status` param isn't translated --
 * the canonical page's filter keys (`view`/`stage`) don't share the same
 * value space, and this file's own prior policy was to drop legacy-only
 * params rather than silently map them to the wrong filter.
 */
import { redirect } from "next/navigation";

export default function LegacyOperationsRedirect() {
  redirect("/admin/home-services/bookings-jobs");
}
