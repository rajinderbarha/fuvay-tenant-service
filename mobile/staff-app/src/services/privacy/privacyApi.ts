import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import {
  PrivacySummaryDTO, ConsentPurposeDTO, ConsentHistoryItemDTO, PrivacyRequestType,
  RequestSummaryDTO, RequestDetailDTO, ExportStatusDTO,
} from "./types";

const BASE = "/v1/me/privacy";

export function getSummary(signal?: AbortSignal): Promise<ApiResult<PrivacySummaryDTO>> {
  return authenticatedRequest<PrivacySummaryDTO>(`${BASE}/summary`, { method: "GET", signal });
}

export function getConsents(signal?: AbortSignal): Promise<ApiResult<{ consents: ConsentPurposeDTO[] }>> {
  return authenticatedRequest(`${BASE}/consents`, { method: "GET", signal });
}

export function updateConsent(purposeCode: string, enabled: boolean): Promise<ApiResult<{ purpose_code: string; enabled: boolean }>> {
  return authenticatedRequest(`${BASE}/consents/${purposeCode}`, { method: "PATCH", body: { enabled } });
}

export function getConsentHistory(signal?: AbortSignal): Promise<ApiResult<{ items: ConsentHistoryItemDTO[]; meta: { total: number } }>> {
  return authenticatedRequest(`${BASE}/consent-history`, { method: "GET", signal });
}

export function listRequests(signal?: AbortSignal): Promise<ApiResult<{ requests: RequestSummaryDTO[] }>> {
  return authenticatedRequest(`${BASE}/requests`, { method: "GET", signal });
}

export function submitRequest(input: {
  requestType: PrivacyRequestType; reason: string; details?: string; isAccountClosure?: boolean;
}): Promise<ApiResult<{ request_id: string; request_number: string; status: string; message: string }>> {
  return authenticatedRequest(`${BASE}/requests`, {
    method: "POST",
    body: {
      request_type: input.requestType, reason: input.reason, details: input.details ?? "",
      confirm_understanding: true, is_account_closure: !!input.isAccountClosure,
    },
  });
}

export function getRequestDetail(requestId: string, signal?: AbortSignal): Promise<ApiResult<RequestDetailDTO>> {
  return authenticatedRequest(`${BASE}/requests/${requestId}`, { method: "GET", signal });
}

export function withdrawRequest(requestId: string): Promise<ApiResult<{ withdrawn: boolean }>> {
  return authenticatedRequest(`${BASE}/requests/${requestId}/withdraw`, { method: "POST" });
}

export function generateExport(requestId: string): Promise<ApiResult<{ export_id: string; status: string; expires_at: string; message: string }>> {
  return authenticatedRequest(`${BASE}/requests/${requestId}/generate-export`, { method: "POST" });
}

export function getExport(exportId: string, signal?: AbortSignal): Promise<ApiResult<ExportStatusDTO>> {
  return authenticatedRequest(`${BASE}/exports/${exportId}`, { method: "GET", signal });
}
