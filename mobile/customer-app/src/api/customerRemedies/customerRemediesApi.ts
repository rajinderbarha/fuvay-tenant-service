import { z } from "zod";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  refundRequestListSchema,
  refundRequestSchema,
  warrantyClaimListSchema,
  warrantyClaimSchema,
} from "../contracts/customerRemedies";

export async function listMyWarrantyClaims() {
  const response = await authenticatedRequest({ method: "GET", path: "/v1/commerce/customer/warranty/claims" });
  return parseApiSuccess(response.json, warrantyClaimListSchema);
}

export async function submitWarrantyClaim(jobId: string, description: string, amount?: number) {
  const response = await authenticatedRequest({
    method: "POST",
    path: "/v1/commerce/warranty/claims",
    body: {
      job_id: jobId,
      claim_type: "service_quality",
      description,
      media_ids: [],
      ...(amount && amount > 0 ? { amount_requested: amount } : {}),
    },
  });
  return parseApiSuccess(response.json, warrantyClaimSchema);
}

export async function escalateWarrantyClaim(claimId: string, reason: string) {
  const response = await authenticatedRequest({
    method: "POST", path: `/v1/commerce/warranty/claims/${claimId}/escalate`, body: { reason },
  });
  return parseApiSuccess(response.json, warrantyClaimSchema);
}

export async function listMyRefundRequests() {
  const response = await authenticatedRequest({ method: "GET", path: "/v1/customer/complaints/records/refunds" });
  return parseApiSuccess(response.json, refundRequestListSchema);
}

export async function submitRefundRequest(jobId: string, description: string, amount: number) {
  const response = await authenticatedRequest({
    method: "POST",
    path: "/v1/customer/complaints/records/refunds/from-job",
    body: {
      job_id: jobId,
      reason: description,
      requested_amount: amount,
    },
  });
  return parseApiSuccess(response.json, refundRequestSchema);
}

export async function escalateRefundRequest(refundId: string, reason: string) {
  const response = await authenticatedRequest({
    method: "POST", path: `/v1/customer/complaints/refunds/${refundId}/escalate`, body: { reason },
  });
  return parseApiSuccess(response.json, refundRequestSchema);
}

export const remedySubmissionSchema = z.object({ description: z.string().min(20), amount: z.number().positive().optional() });
