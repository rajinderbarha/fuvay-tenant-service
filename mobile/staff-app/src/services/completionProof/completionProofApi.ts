import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { CompletionProofDetailDTO, CompletionProofDTO } from "./types";

export function getCompletionProofDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<CompletionProofDetailDTO>> {
  return authenticatedRequest<CompletionProofDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof`, { method: "GET", signal });
}

export function saveDraft(jobId: string, body: { resolution_summary?: string; final_service_notes?: string }): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/draft`, { method: "PUT", body });
}

export function addEvidence(jobId: string, category: "before" | "after", fileId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/evidence`, { method: "POST", body: { category, file_id: fileId } });
}

export function removeEvidence(jobId: string, category: "before" | "after", fileId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/evidence/${category}/${fileId}`, { method: "DELETE" });
}

export function submitCompletionProof(jobId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/submit`, { method: "POST", unsafeToRetry: true });
}

export function requestHandover(jobId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/request-handover`, { method: "POST", unsafeToRetry: true });
}

export function sendHandoverReminder(jobId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/send-reminder`, { method: "POST", unsafeToRetry: true });
}

export function markCustomerUnavailable(jobId: string): Promise<ApiResult<CompletionProofDTO>> {
  return authenticatedRequest<CompletionProofDTO>(`/v1/staff/service-jobs/${jobId}/mobile-completion-proof/customer-unavailable`, { method: "POST", unsafeToRetry: true });
}
