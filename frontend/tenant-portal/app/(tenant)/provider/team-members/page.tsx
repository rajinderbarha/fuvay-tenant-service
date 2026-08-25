import { redirect } from "next/navigation";

/** Retired alias. The Home Services roster is the single provider team
 * workspace; preserving this redirect keeps old bookmarks non-breaking. */
export default function RetiredProviderTeamMembersPage() {
  redirect("/home-services/team");
}
