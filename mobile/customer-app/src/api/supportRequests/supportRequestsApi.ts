import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  supportRequestListResponseSchema, supportRequestDtoSchema,
  createSupportRequestBodySchema, CreateSupportRequestBody,
  supportRequestMessageListResponseSchema,
} from "../contracts/supportRequests";
import { z } from "zod";

const BASE = "/v1/customer/complaints";

export async function listMySupportRequests() {
  const res = await authenticatedRequest({ method: "GET", path: BASE });
  return parseApiSuccess(res.json, supportRequestListResponseSchema);
}

export async function createMySupportRequest(body: CreateSupportRequestBody) {
  const parsed = createSupportRequestBodySchema.parse(body);
  const res = await authenticatedRequest({ method: "POST", path: BASE, body: parsed });
  return parseApiSuccess(res.json, supportRequestDtoSchema);
}

export async function getMySupportRequest(requestId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/${requestId}` });
  return parseApiSuccess(res.json, supportRequestDtoSchema);
}

export async function cancelMySupportRequest(requestId: string, reason: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `${BASE}/${requestId}/cancel`, body: { reason },
  });
  return parseApiSuccess(res.json, z.object({ id: z.string(), status: z.string() }));
}

export async function listMySupportRequestMessages(requestId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/${requestId}/messages` });
  return parseApiSuccess(res.json, supportRequestMessageListResponseSchema);
}

export async function addMySupportRequestMessage(requestId: string, messageText: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `${BASE}/${requestId}/messages`, body: { message_text: messageText },
  });
  return parseApiSuccess(res.json, z.object({ id: z.string(), message_text: z.string() }));
}
