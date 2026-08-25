import { redirect } from "next/navigation";

/** Legacy generic dispatch route.
 *
 * Home Services jobs live in service_jobs and use the canonical provider
 * assignment workflow. The retired generic page queried field_ops jobs,
 * which has no Home Services records, so it is now a compatibility redirect
 * instead of presenting a second, empty dispatch system.
 */
export default function LegacyDispatchRedirect() {
  redirect("/home-services/dispatch");
}
