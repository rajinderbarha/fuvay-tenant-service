/**
 * FINAL-L5-05E — legacy Field Ops Job detail, superseded by the canonical
 * service_jobs-backed detail page. Legacy `jobs.id` values are not the same
 * identifier space as canonical `service_jobs.id` -- there is no guaranteed
 * 1:1 mapping, so this redirects to the canonical Jobs list (not a guessed
 * canonical detail URL) with the legacy id preserved as a query param for
 * reference. No jobsApi/`/v1/jobs` data is fetched by this route anymore.
 */
import { redirect } from "next/navigation";

export default async function LegacyOperationsJobRedirect({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  redirect(`/admin/home-services/service-jobs?legacy_id=${encodeURIComponent(jobId)}`);
}
