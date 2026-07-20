import { apiClient } from "../../../api/api-client";

/**
 * Real path verified against
 * app/engines/execution/home_service_router.py — see
 * CUSTOMER-L5-13-contract-matrix.md. Requires a real `ServiceJob.id`
 * (`jobId`), obtained via the reused CUSTOMER-L5-11 booking-detail
 * endpoint (`features/booking-confirmation`) — no other real customer
 * endpoint returns a raw job ID.
 */
export const serviceTrackingApi = {
  getJobTracking: (jobId: string, options: { signal?: AbortSignal } = {}) =>
    apiClient.get<unknown>(`/v1/customer/service-jobs/${encodeURIComponent(jobId)}/tracking`, { signal: options.signal }),
};
