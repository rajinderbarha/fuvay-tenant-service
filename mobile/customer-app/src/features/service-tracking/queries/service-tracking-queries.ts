import { useQuery } from "@tanstack/react-query";
import { serviceTrackingApi } from "../api/service-tracking-api";
import { parseExecutionTracking } from "../domain/execution-timeline-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

export const serviceTrackingQueryKeys = {
  timeline: (jobId: string, locale: string, tenantId: string | undefined) => ["serviceTracking", "timeline", jobId, locale, tenantId ?? "no-tenant"] as const,
};

/** Real query — the execution timeline is a stateless, always-re-fetchable resource (no session/authorization concept exists, contract-matrix.md). */
export function useJobExecutionTracking(jobId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: serviceTrackingQueryKeys.timeline(jobId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await serviceTrackingApi.getJobTracking(jobId as string, { signal });
      const parsed = parseExecutionTracking(response);
      if (!parsed) {
        logger.warn("service_tracking_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Service tracking response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: Boolean(jobId),
    staleTime: 0,
    retry: 1,
  });
}
