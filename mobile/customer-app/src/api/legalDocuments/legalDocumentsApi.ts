import { request } from "../client/httpClient";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { z } from "zod";
import {
  legalDocumentIndexSchema, legalDocumentSchema,
} from "../contracts/legalDocuments";

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
  const res = await authenticatedRequest({ method: "GET", path: "/v1/legal/consent-status" });
  return parseApiSuccess(res.json, legalConsentStatusSchema).data;
}

export async function acceptLegalDocuments(documentIds: string[]): Promise<LegalConsentStatus> {
  const res = await authenticatedRequest({
    method: "POST",
    path: "/v1/legal/accept",
    body: { accepted: true, document_ids: documentIds },
  });
  return parseApiSuccess(res.json, legalConsentStatusSchema).data;
}
