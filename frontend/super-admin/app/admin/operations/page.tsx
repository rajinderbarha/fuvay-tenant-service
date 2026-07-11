/**
 * FINAL-L5-05E — legacy Field Ops Jobs list, superseded by the canonical
 * service_jobs-backed page at /admin/home-services/service-jobs (parity
 * proven: reassign/status-override/force-close/void/SLA/summary all real
 * and live against service_jobs; see docs/final-l5-05/
 * FINAL_L5_05B_JOBS_MIGRATION.md). This route is now a compatibility
 * redirect only -- it no longer fetches jobsApi/`/v1/jobs` data.
 * Preserves the `status` query param where the canonical page uses the
 * same filter key; other legacy-only filter params are dropped rather
 * than silently mapped to a wrong canonical filter.
 */
import { redirect } from "next/navigation";

export default async function LegacyOperationsRedirect({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const status = typeof params.status === "string" ? params.status : undefined;
  const target = status
    ? `/admin/home-services/service-jobs?status=${encodeURIComponent(status)}`
    : "/admin/home-services/service-jobs";
  redirect(target);
}
