import { request } from "../client/httpClient";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { z } from "zod";
import {
  legalDocumentIndexSchema, legalDocumentSchema,
} from "../contracts/legalDocuments";
import { ENV } from "../../config/environment";

/**
 * Legal documents — public read client.
 *
 * Calls `request` directly rather than `authenticatedRequest`: these
 * endpoints take no session, and the login/signup screens that link to them
 * run when there is no token at all. Routing them through the authenticated
 * wrapper would attach a stale token and, worse, could trip its 401
 * refresh-and-logout path for a page that never needed auth.
 */

const BASE = "/v1/public/legal";
// This request runs immediately after authentication, when the API may still be
// warming its legal-document cache or database connection. It gates the entire
// signed-in experience, so give it a little more room than ordinary screen data
// instead of stranding a successfully authenticated customer on a timeout page.
const CONSENT_TIMEOUT_MS = 30_000;

export const CUSTOMER_AUDIENCE = "customer";

export async function listLegalDocuments(audience: string = CUSTOMER_AUDIENCE) {
  const res = await request({
    method: "GET",
    path: `${BASE}?audience=${encodeURIComponent(audience)}`,
  });
  return parseApiSuccess(res.json, legalDocumentIndexSchema);
}

export async function getLegalDocument(
  docType: string,
  audience: string = CUSTOMER_AUDIENCE,
) {
  const res = await request({
    method: "GET",
    path: `${BASE}/${encodeURIComponent(docType)}?audience=${encodeURIComponent(audience)}`,
  });
  return parseApiSuccess(res.json, legalDocumentSchema);
}

const legalConsentStatusSchema = z.object({
  requires_acceptance: z.boolean(),
  documents: z.array(legalDocumentSchema),
  document_ids: z.array(z.string().uuid()),
  message: z.string(),
});

export type LegalConsentStatus = z.infer<typeof legalConsentStatusSchema>;

export async function getLegalConsentStatus(): Promise<LegalConsentStatus> {
  const res = await authenticatedRequest({
    method: "GET",
    path: "/v1/legal/consent-status",
    timeoutMs: Math.max(ENV.apiTimeoutMs, CONSENT_TIMEOUT_MS),
  });
  return parseApiSuccess(res.json, legalConsentStatusSchema).data;
}

export async function acceptLegalDocuments(documentIds: string[]): Promise<LegalConsentStatus> {
  const res = await authenticatedRequest({
    method: "POST",
    path: "/v1/legal/accept",
    body: { accepted: true, document_ids: documentIds },
    timeoutMs: Math.max(ENV.apiTimeoutMs, CONSENT_TIMEOUT_MS),
  });
  return parseApiSuccess(res.json, legalConsentStatusSchema).data;
}
