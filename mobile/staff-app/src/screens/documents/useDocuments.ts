import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/documents/documentsApi";
import { uploadStaffDocument } from "../../services/media/mediaApi";
import { useSession } from "../../navigation/session/SessionProvider";
import { AppError } from "../../services/api/types";

const QUERY_KEY = ["staff-documents"] as const;

/** Documents & Certifications (Phase T). Readiness/status/versioning are
 * entirely backend-calculated over the canonical TenantDocument model --
 * this hook never computes a percentage or review state locally. */
export function useDocuments() {
  const queryClient = useQueryClient();
  const { accessContext } = useSession();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getDocuments(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const refresh = useCallback(() => queryClient.invalidateQueries({ queryKey: QUERY_KEY }), [queryClient]);

  const submit = useCallback(async (
    docType: string, fileUri: string, fileName: string, mimeType: string,
    extra?: { documentNumber?: string; issueDate?: string; expiryDate?: string },
  ) => {
    if (uploading || !accessContext.userId) return { ok: false as const };
    setUploading(true);
    setUploadError(null);
    try {
      const upload = await uploadStaffDocument(fileUri, fileName, mimeType, accessContext.userId);
      if (!upload.ok) {
        setUploadError(upload.error);
        return { ok: false as const };
      }
      const result = await api.submitDocument({ docType, mediaAssetId: upload.data.id, ...extra });
      if (!result.ok) {
        setUploadError(result.error);
        return { ok: false as const };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setUploading(false);
    }
  }, [uploading, refresh, accessContext.userId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    uploading, uploadError,
    submit,
  };
}
