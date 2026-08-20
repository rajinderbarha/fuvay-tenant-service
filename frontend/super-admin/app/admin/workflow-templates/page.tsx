import { redirect } from "next/navigation";

/**
 * Retired duplicate surface.
 *
 * Workflow authoring is now owned by the Home Services Catalog Workspace's
 * Job-Type Blueprint workflow tab, backed by `service_job_workflow`. That is
 * the workflow id snapshotted by bookings/jobs and rendered by customer,
 * tenant/provider, staff, and admin job surfaces.
 *
 * This old page edited `master_workflow_templates`, which is not read by the
 * runtime execution chain. Keep the URL as a safe redirect for bookmarks, but
 * do not render another editor here.
 */
export default function RetiredWorkflowTemplatesPage() {
  redirect("/admin/catalog-workspace?tab=workflow");
}
