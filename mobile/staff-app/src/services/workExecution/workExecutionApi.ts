import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { WorkExecutionDetailDTO, WorkSessionDTO, PartsRequestDTO } from "./types";

export function getWorkExecutionDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<WorkExecutionDetailDTO>> {
  return authenticatedRequest<WorkExecutionDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-work-execution`, { method: "GET", signal });
}

export function startWork(jobId: string): Promise<ApiResult<WorkSessionDTO>> {
  return authenticatedRequest<WorkSessionDTO>(`/v1/staff/service-jobs/${jobId}/mobile-work-execution/start`, { method: "POST", unsafeToRetry: true });
}

export function pauseWork(jobId: string, reason?: string): Promise<ApiResult<WorkSessionDTO>> {
  return authenticatedRequest<WorkSessionDTO>(`/v1/staff/service-jobs/${jobId}/mobile-work-execution/pause`, { method: "POST", body: { reason: reason ?? null }, unsafeToRetry: true });
}

export function resumeWork(jobId: string): Promise<ApiResult<WorkSessionDTO>> {
  return authenticatedRequest<WorkSessionDTO>(`/v1/staff/service-jobs/${jobId}/mobile-work-execution/resume`, { method: "POST", unsafeToRetry: true });
}

export function finishWork(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-work-execution/finish`, { method: "POST", unsafeToRetry: true });
}

/** Reuses the EXISTING, already-technician-authorized parts-request endpoint
 * (app/engines/execution/home_service_router.py) -- never a second parts engine. */
export function createPartsRequest(jobId: string, body: {
  part_name: string; quantity: number; estimated_cost: number; reason: string;
  technician_note?: string; customer_approval_required?: boolean;
}): Promise<ApiResult<PartsRequestDTO>> {
  return authenticatedRequest<PartsRequestDTO>(`/v1/staff/service-jobs/${jobId}/parts-requests`, { method: "POST", body });
}

/** Reuses the EXISTING checklist_catalog staff response endpoint. */
export function saveWorkChecklistResponse(
  instanceId: string, itemId: string,
  responseValue: Record<string, unknown> | null,
  evidence: { file_id: string }[] | null,
): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/checklist-instances/${instanceId}/responses/${itemId}`, {
    method: "POST", body: { response_value: responseValue, evidence }, unsafeToRetry: true,
  });
}
