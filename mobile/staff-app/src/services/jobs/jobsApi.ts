import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { MobileJobsDTO, JobsQueryParams } from "./types";

/** GET /v1/staff/mobile-jobs (Phase I, app/engines/execution/mobile_jobs_router.py). */
export function getMobileJobs(
  params: JobsQueryParams & { cursor?: string | null; limit?: number },
  signal?: AbortSignal,
): Promise<ApiResult<MobileJobsDTO>> {
  return authenticatedRequest<MobileJobsDTO>("/v1/staff/mobile-jobs", {
    method: "GET",
    signal,
    query: {
      view: params.view,
      search: params.search || undefined,
      workflow_status: params.workflowStatus || undefined,
      action_required: params.actionRequired || undefined,
      cursor: params.cursor || undefined,
      limit: params.limit ?? 20,
    },
  });
}
