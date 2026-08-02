import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/profile/profileApi";
import { uploadStaffDocument } from "../../services/media/mediaApi";
import { useSession } from "../../navigation/session/SessionProvider";
import { AppError } from "../../services/api/types";

const QUERY_KEY = ["profile"] as const;

/** Profile hub data + guarded document submission (Phase R). Employment/
 * tenant-controlled fields are never mutated from this hook -- read-only
 * by design (spec section 4). */
export function useProfile() {
  const queryClient = useQueryClient();
  const { accessContext } = useSession();
  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getProfile(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const refresh = useCallback(() => queryClient.invalidateQueries({ queryKey: QUERY_KEY }), [queryClient]);

  const submitDocument = useCallback(async (documentType: string, fileUri: string, fileName: string, mimeType: string) => {
    if (mutating || !accessContext.userId) return { ok: false as const };
    setMutating(true);
    setMutationError(null);
    try {
      const upload = await uploadStaffDocument(fileUri, fileName, mimeType, accessContext.userId);
      if (!upload.ok) {
        setMutationError(upload.error);
        return { ok: false as const };
      }
      const result = await api.addDocument(documentType, upload.data.id);
      if (!result.ok) {
        setMutationError(result.error);
        return { ok: false as const };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setMutating(false);
    }
  }, [mutating, refresh, accessContext.userId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError,
    submitDocument,
  };
}
