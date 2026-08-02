import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { DirectPaymentDetailDTO, ProviderRecordDTO, DirectPaymentMethod } from "./types";

export function getDirectPaymentDetail(jobId: string, signal?: AbortSignal): Promise<ApiResult<DirectPaymentDetailDTO>> {
  return authenticatedRequest<DirectPaymentDetailDTO>(`/v1/staff/service-jobs/${jobId}/mobile-direct-payment`, { method: "GET", signal });
}

export function declarePayment(jobId: string, body: {
  amount: string; method: DirectPaymentMethod; reference_id?: string; note?: string; evidence_media_id?: string;
}): Promise<ApiResult<ProviderRecordDTO>> {
  return authenticatedRequest<ProviderRecordDTO>(`/v1/staff/service-jobs/${jobId}/mobile-direct-payment/declare`, { method: "POST", body, unsafeToRetry: true });
}

export function remindCustomer(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-direct-payment/remind`, { method: "POST", unsafeToRetry: true });
}

export function finalizeJob(jobId: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/service-jobs/${jobId}/mobile-direct-payment/finalize`, { method: "POST", unsafeToRetry: true });
}
