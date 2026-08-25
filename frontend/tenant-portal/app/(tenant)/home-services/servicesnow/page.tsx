import { redirect } from "next/navigation";

/**
 * Compatibility route for an old internal link. Services & Pricing has one
 * canonical workspace so setup, dashboard navigation and saved bookmarks do
 * not drift into separate implementations.
 */
export default function ServicesNowRedirect() {
  redirect("/home-services/services");
}
