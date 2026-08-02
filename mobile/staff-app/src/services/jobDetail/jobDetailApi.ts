import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { JobMobileDetailDTO, JobTimelineDTO } from "./types";

/** GET /v1/staff/service-jobs/{job_id}/mobile-detail (Phase J). */
export function getJobDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<JobMobileDetailDTO>> {
  return authenticatedRequest<JobMobileDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-detail`, { method: "GET", signal });
}

/** GET /v1/staff/service-jobs/{job_id}/mobile-timeline (Phase J). */
export function getJobTimeline(jobId: string, signal?: AbortSignal): Promise<ApiResult<JobTimelineDTO>> {
  return authenticatedRequest<JobTimelineDTO>(`/v1/staff/service-jobs/${jobId}/mobile-timeline`, { method: "GET", signal });
}

/**
 * Simple, already-supported transitions only (spec section 8) -- these
 * call the REAL existing execution endpoints
 * (app/engines/execution/home_service_router.py), never a new mobile-only
 * mutation. Neither endpoint accepts a body/version/idempotency key today
 * (audited) -- duplicate-submission protection is enforced client-side
 * (busy-state guard) until the backend adds one.
 */
export function acceptJob(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/accept`, { method: "POST", unsafeToRetry: true });
}

export function startTravel(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/on-the-way`, { method: "POST", unsafeToRetry: true });
}

export function markArrived(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/reached-site`, { method: "POST", unsafeToRetry: true });
}
