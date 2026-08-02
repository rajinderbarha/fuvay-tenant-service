import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { EmploymentDetailDTO, PermissionsSummaryDTO, CorrectionRequestDTO, CorrectionFieldKey } from "./types";

export function getEmploymentDetails(signal?: AbortSignal): Promise<ApiResult<EmploymentDetailDTO>> {
  return authenticatedRequest<EmploymentDetailDTO>(`/v1/staff/me/employment-details`, { method: "GET", signal });
}

export function getPermissionsSummary(signal?: AbortSignal): Promise<ApiResult<PermissionsSummaryDTO>> {
  return authenticatedRequest<PermissionsSummaryDTO>(`/v1/staff/me/employment-details/permissions`, { method: "GET", signal });
}

export function submitCorrectionRequest(input: {
  fieldKey: CorrectionFieldKey; requestedValue: string; reason: string;
}): Promise<ApiResult<CorrectionRequestDTO>> {
  return authenticatedRequest<CorrectionRequestDTO>(`/v1/staff/me/employment-correction-requests`, {
    method: "POST",
    body: { field_key: input.fieldKey, requested_value: input.requestedValue, reason: input.reason },
  });
}

export function listCorrectionRequests(signal?: AbortSignal): Promise<ApiResult<{ requests: CorrectionRequestDTO[] }>> {
  return authenticatedRequest<{ requests: CorrectionRequestDTO[] }>(`/v1/staff/me/employment-correction-requests`, { method: "GET", signal });
}
