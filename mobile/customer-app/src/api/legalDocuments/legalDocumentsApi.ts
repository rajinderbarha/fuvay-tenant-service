import { request } from "../client/httpClient";
import { parseApiSuccess } from "../client/responseParser";
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
