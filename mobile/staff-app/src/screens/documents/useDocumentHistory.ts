import { useQuery } from "@tanstack/react-query";
import * as api from "../../services/documents/documentsApi";

export function useDocumentHistory(docType: string) {
  const query = useQuery({
    queryKey: ["staff-document-history", docType],
    queryFn: async ({ signal }) => {
      const result = await api.getDocumentHistory(docType, signal);
      if (!result.ok) throw result.error;
      return result.data.versions;
    },
  });
  return { versions: query.data ?? [], isLoading: query.isLoading, isError: query.isError, refetch: query.refetch };
}
