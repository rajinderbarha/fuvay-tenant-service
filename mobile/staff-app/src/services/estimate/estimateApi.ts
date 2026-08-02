import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { EstimateDetailDTO, QuoteDTO, QuoteItemType } from "./types";

export function getEstimateDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<EstimateDetailDTO>> {
  return authenticatedRequest<EstimateDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-estimate`, { method: "GET", signal });
}

export function createEstimate(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-estimate/create`, { method: "POST", unsafeToRetry: true });
}

export function createRevision(jobId: string, currentQuoteId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-estimate/${currentQuoteId}/revise`, { method: "POST", unsafeToRetry: true });
}

export function addEstimateItem(
  jobId: string, quoteId: string,
  item: { item_type: QuoteItemType; item_name: string; item_description?: string; quantity: number; unit_price: number },
): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-estimate/${quoteId}/items`, { method: "POST", body: item });
}

export function updateEstimateItem(
  jobId: string, quoteId: string, itemId: string,
  patch: { item_name?: string; item_description?: string; quantity?: number; unit_price?: number },
): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-estimate/${quoteId}/items/${itemId}`, { method: "PUT", body: patch });
}

export function removeEstimateItem(jobId: string, quoteId: string, itemId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-estimate/${quoteId}/items/${itemId}`, { method: "DELETE" });
}

export function sendEstimateForApproval(jobId: string, quoteId: string, customerNotes?: string): Promise<ApiResult<QuoteDTO>> {
  return authenticatedRequest<QuoteDTO>(`/v1/staff/service-jobs/${jobId}/mobile-estimate/${quoteId}/send`, {
    method: "POST", body: { customer_notes: customerNotes ?? null }, unsafeToRetry: true,
  });
}
