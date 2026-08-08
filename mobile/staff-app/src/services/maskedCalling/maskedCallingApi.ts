import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";

/**
 * Masked calling — the platform bridges the technician and the customer so
 * neither ever sees the other's number.
 *
 * There is deliberately no field on either response that could carry a phone
 * number: the backend does not send one in any state, and this client does not
 * declare one, so no future screen can accidentally render it. When a call
 * cannot be placed, `cannot_call_reason` says why -- the UI must show that
 * rather than falling back to any other contact route.
 */

export interface MaskedContactDTO {
  job_id: string;
  customer_display: string;
  /** Always false. Present so a reader sees the absence is intentional. */
  phone_number_visible: boolean;
  phone_number_policy: string;
  can_call: boolean;
  cannot_call_reason: string | null;
  /** True once a bridged call to this customer has genuinely CONNECTED --
   * which is what satisfies the "call the customer first" task. */
  connected_before: boolean;
  last_call: MaskedCallSessionDTO | null;
}

export interface MaskedCallSessionDTO {
  id: string;
  job_id: string;
  status: string;
  direction: string;
  /** The platform's own number, which both parties see. Not sensitive. */
  caller_id_used: string | null;
  failure_reason: string | null;
  duration_seconds: number | null;
  connected_at: string | null;
  ended_at: string | null;
  expires_at: string | null;
}

/** GET /v1/staff/service-jobs/{job_id}/contact */
export function getContact(jobId: string, signal?: AbortSignal): Promise<ApiResult<MaskedContactDTO>> {
  return authenticatedRequest<MaskedContactDTO>(
    `/v1/staff/service-jobs/${jobId}/contact`, { method: "GET", signal });
}

/**
 * POST /v1/staff/service-jobs/{job_id}/call
 *
 * `unsafeToRetry` because a retry would place a SECOND real phone call --
 * the customer's phone ringing twice is a real-world side effect, not an
 * idempotent write.
 */
export function callCustomer(jobId: string): Promise<ApiResult<MaskedCallSessionDTO>> {
  return authenticatedRequest<MaskedCallSessionDTO>(
    `/v1/staff/service-jobs/${jobId}/call`, { method: "POST", unsafeToRetry: true });
}
