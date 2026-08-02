import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { InspectionDetailDTO, ChecklistResponseDTO } from "./types";

/** GET /v1/staff/service-jobs/{job_id}/mobile-inspection (Phase K). */
export function getInspectionDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<InspectionDetailDTO>> {
  return authenticatedRequest<InspectionDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-inspection`, { method: "GET", signal });
}

/**
 * Save/draft an item response. Reuses the EXISTING, already-tested
 * checklist_catalog staff endpoint directly (spec: never duplicate the
 * write path) -- see app/engines/checklist_catalog/execution_router.py.
 */
export function saveChecklistItemResponse(
  instanceId: string, itemId: string,
  responseValue: Record<string, unknown> | null,
  evidence: { file_id: string }[] | null,
): Promise<ApiResult<ChecklistResponseDTO>> {
  return authenticatedRequest<ChecklistResponseDTO>(
    `/v1/staff/service-jobs/checklist-instances/${instanceId}/responses/${itemId}`,
    { method: "POST", body: { response_value: responseValue, evidence }, unsafeToRetry: true },
  );
}

/** Reuses the existing checklist-instance completion endpoint. */
export function completeChecklistInstance(instanceId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/checklist-instances/${instanceId}/complete`, { method: "POST", unsafeToRetry: true });
}

/** Reuses the existing execution workflow transition (asserts the same
 * completion gate a second time server-side -- backend remains authoritative). */
export function completeInspectionWorkflow(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/complete-inspection`, { method: "POST", unsafeToRetry: true });
}
