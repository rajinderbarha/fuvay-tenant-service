import { useQuery } from "@tanstack/react-query";

import { getLegalDocument, listLegalDocuments } from "./legalDocumentsApi";

/** Query keys for the public legal documents. */
export const legalQueryKeys = {
  index: (audience: string) => ["legal", "index", audience] as const,
  document: (docType: string, audience: string) =>
    ["legal", "document", docType, audience] as const,
};

/**
 * Published legal documents change on the order of months, so the cache is
 * deliberately long-lived: re-fetching the full Terms text on every screen
 * focus would be pure waste. `staleTime` still lets a publish reach the app
 * within the hour without a release.
 */
const STALE_MS = 60 * 60 * 1000;

export function useLegalDocumentIndexQuery(audience: string = "customer") {
  return useQuery({
    queryKey: legalQueryKeys.index(audience),
    queryFn: async () => (await listLegalDocuments(audience)).data,
    staleTime: STALE_MS,
  });
}

export function useLegalDocumentQuery(docType: string, audience: string = "customer") {
  return useQuery({
    queryKey: legalQueryKeys.document(docType, audience),
    queryFn: async () => (await getLegalDocument(docType, audience)).data,
    staleTime: STALE_MS,
    enabled: !!docType,
  });
}
