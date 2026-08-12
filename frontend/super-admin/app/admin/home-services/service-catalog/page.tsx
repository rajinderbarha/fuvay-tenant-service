import { redirect } from "next/navigation";

// This page was replaced by the Admin Catalog Workspace (dimensions, problems
// & questions with a show-when rule builder, tenant setup rules, blueprint
// readiness, job types) -- redirecting so old links/bookmarks keep working.
export default function LegacyHomeServicesCatalogRedirect() {
  redirect("/admin/catalog-workspace");
}
