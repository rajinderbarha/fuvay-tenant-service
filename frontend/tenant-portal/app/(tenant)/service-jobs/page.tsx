import { redirect } from "next/navigation";

/** Compatibility route for old notification rows and saved bookmarks. */
export default function LegacyServiceJobsPage() {
  redirect("/home-services/bookings-jobs");
}
