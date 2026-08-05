import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  privacyRequestListResponseSchema, privacyRequestDtoSchema,
  createPrivacyRequestBodySchema, CreatePrivacyRequestBody, createPrivacyRequestResponseSchema,
  consentListResponseSchema, exportDownloadResponseSchema,
} from "../contracts/privacyData";
import { z } from "zod";

const BASE = "/v1/me/compliance";

export async function listMyPrivacyRequests(page: number = 1, limit: number = 20) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/requests?page=${page}&limit=${limit}` });
  return parseApiSuccess(res.json, privacyRequestListResponseSchema);
}

export async function createMyPrivacyRequest(body: CreatePrivacyRequestBody) {
  const parsed = createPrivacyRequestBodySchema.parse(body);
  const res = await authenticatedRequest({ method: "POST", path: `${BASE}/requests`, body: parsed });
  return parseApiSuccess(res.json, createPrivacyRequestResponseSchema);
}

export async function getMyPrivacyRequest(requestId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/requests/${requestId}` });
  return parseApiSuccess(res.json, privacyRequestDtoSchema);
}

export async function cancelMyPrivacyRequest(requestId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${BASE}/requests/${requestId}/cancel` });
  return parseApiSuccess(res.json, z.object({ cancelled: z.boolean(), request_id: z.string() }));
}

export async function listMyConsents() {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/consents` });
  return parseApiSuccess(res.json, consentListResponseSchema);
}

export async function withdrawMyConsent(consentType: string, reason?: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `${BASE}/consents/${consentType}/withdraw`,
    body: { reason },
  });
  return parseApiSuccess(res.json, z.object({ withdrawn: z.boolean(), consent_type: z.string() }));
}

export async function downloadMyExport(exportId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/exports/${exportId}/download` });
  return parseApiSuccess(res.json, exportDownloadResponseSchema);
}
