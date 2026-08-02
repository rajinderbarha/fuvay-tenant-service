import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as inspectionApi from "../../services/inspection/inspectionApi";
import { uploadChecklistEvidence } from "../../services/media/mediaApi";
import { AppError } from "../../services/api/types";

function queryKey(jobId: string) {
  return ["jobs", "inspection", jobId] as const;
}

/**
 * Inspection data + guarded mutations (Phase K spec sections 9, 10, 17).
 * Every save/complete result is discarded in favor of a fresh authoritative
 * refetch -- never optimistic checklist progress.
 */
export function useInspection(jobId: string) {
  const queryClient = useQueryClient();
  const key = queryKey(jobId);

  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<AppError | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<AppError | null>(null);
  const [uploadingItemId, setUploadingItemId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await inspectionApi.getInspectionDetail(jobId, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled: Boolean(jobId),
  });

  const refresh = useCallback(() => queryClient.invalidateQueries({ queryKey: key }), [queryClient, key]);

  const saveItemResponse = useCallback(async (
    instanceId: string, itemId: string,
    responseValue: Record<string, unknown> | null,
    evidence: { file_id: string }[] | null,
  ) => {
    if (savingItemId) return { ok: false as const };
    setSavingItemId(itemId);
    setSaveError(null);
    try {
      const result = await inspectionApi.saveChecklistItemResponse(instanceId, itemId, responseValue, evidence);
      if (!result.ok) {
        setSaveError(result.error);
        return { ok: false as const, error: result.error };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setSavingItemId(null);
    }
  }, [savingItemId, refresh]);

  const uploadEvidence = useCallback(async (itemId: string, fileUri: string, fileName: string, mimeType: string) => {
    if (uploadingItemId) return { ok: false as const };
    setUploadingItemId(itemId);
    setUploadError(null);
    try {
      const result = await uploadChecklistEvidence(jobId, fileUri, fileName, mimeType);
      if (!result.ok) {
        setUploadError(result.error);
        return { ok: false as const, error: result.error };
      }
      return { ok: true as const, fileId: result.data.id };
    } finally {
      setUploadingItemId(null);
    }
  }, [uploadingItemId, jobId]);

  const complete = useCallback(async () => {
    if (completing || !query.data?.instance) return { ok: false as const };
    setCompleting(true);
    setCompleteError(null);
    try {
      const instanceResult = await inspectionApi.completeChecklistInstance(query.data.instance.instance_id);
      if (!instanceResult.ok) {
        setCompleteError(instanceResult.error);
        return { ok: false as const, error: instanceResult.error };
      }
      const workflowResult = await inspectionApi.completeInspectionWorkflow(jobId);
      if (!workflowResult.ok) {
        setCompleteError(workflowResult.error);
        return { ok: false as const, error: workflowResult.error };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setCompleting(false);
    }
  }, [completing, query.data, jobId, refresh]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    savingItemId, saveError, saveItemResponse,
    uploadingItemId, uploadError, uploadEvidence,
    completing, completeError, complete,
  };
}
