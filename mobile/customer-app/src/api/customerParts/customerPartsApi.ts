import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { partsRequestListDtoSchema, partsRequestItemDtoSchema } from "../contracts/customerParts";

export async function listJobPartsRequests(jobId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/service-jobs/${jobId}/parts-requests` });
  return parseApiSuccess(res.json, partsRequestListDtoSchema);
}

/** No idempotency-key header -- confirmed via source read of
 * `customer_parts_router.py`, unlike the quote-approve endpoint. Retrying
 * after a genuine decision fails safely server-side
 * (`PARTS_REQUEST_ALREADY_DECIDED`, 409) instead. */
export async function approvePartsRequest(partsRequestId: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/service-jobs/parts-requests/${partsRequestId}/approve`,
  });
  return parseApiSuccess(res.json, partsRequestItemDtoSchema);
}

export async function declinePartsRequest(partsRequestId: string, reason: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/service-jobs/parts-requests/${partsRequestId}/decline`, body: { reason },
  });
  return parseApiSuccess(res.json, partsRequestItemDtoSchema);
}
