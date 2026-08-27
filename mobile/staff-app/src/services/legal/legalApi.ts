import { publicRequest } from "../api/publicClient";

/**
 * Legal documents — public read client for /v1/public/legal/*.
 *
 * Goes through `publicRequest`, not `authenticatedRequest`: the endpoints
 * take no session, and attaching one would put a document anyone may read
 * behind the 401 refresh-and-logout path for no reason.
 */

export interface LegalDocument {
  id: string;
  doc_type: string;
  audience: string;
  locale: string;
  version: string;
  title: string;
  summary: string | null;
  body: string;
  body_format: string;
  effective_at: string | null;
  published_at: string | null;
}

export interface LegalDocumentIndexEntry {
  doc_type: string;
  title: string;
  version: string;
  audience: string;
  locale: string;
  effective_at: string | null;
  path: string;
}

export interface LegalDocumentIndex {
  documents: LegalDocumentIndexEntry[];
  total: number;
}

/** Staff read the provider-facing wording where one exists; the backend
 *  falls back to the shared `all` version automatically. */
export const STAFF_AUDIENCE = "provider";

export function listLegalDocuments(audience: string = STAFF_AUDIENCE) {
  return publicRequest<LegalDocumentIndex>(
    `/v1/public/legal?audience=${encodeURIComponent(audience)}`,
  );
}

export function getLegalDocument(docType: string, audience: string = STAFF_AUDIENCE) {
  return publicRequest<LegalDocument>(
    `/v1/public/legal/${encodeURIComponent(docType)}?audience=${encodeURIComponent(audience)}`,
  );
}
