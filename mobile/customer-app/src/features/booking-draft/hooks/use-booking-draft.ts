import { useEffect, useState } from "react";
import { useDraft, useCreateDraft } from "../queries/draft-queries";
import { getActiveDraftId, setActiveDraftId } from "../state/draft-local-store";
import { logger } from "../../../observability/logger";
import type { ApiError } from "../../../api/api-errors";

export interface UseBookingDraftParams {
  customerId: string | undefined;
  categorySlug: string;
  offeringSlug: string;
}

/**
 * Restoration sequence (CUSTOMER-L5-06 §13): resolve a locally-cached draft
 * ID for this customer → if present, fetch and validate it against the
 * backend (ownership/expiry/status all re-checked server-side by `useDraft`
 * itself) → if absent or the fetch fails, create a new draft. The backend
 * remains the sole canonical source — the local ID is only ever a pointer,
 * never a substitute for a fetch (CUSTOMER-L5-06 §6).
 */
export function useBookingDraft({ customerId, categorySlug, offeringSlug }: UseBookingDraftParams) {
  const [resolvedDraftId, setResolvedDraftId] = useState<string | null | undefined>(undefined);
  const draft = useDraft(resolvedDraftId ?? null);
  const createDraft = useCreateDraft();

  useEffect(() => {
    if (!customerId || resolvedDraftId !== undefined) return;
    let cancelled = false;
    void getActiveDraftId(customerId).then((id) => {
      if (!cancelled) setResolvedDraftId(id);
    });
    return () => {
      cancelled = true;
    };
  }, [customerId, resolvedDraftId]);

  const restoredDraftFailed = resolvedDraftId != null && draft.isError;

  useEffect(() => {
    if (!customerId) return;
    const shouldCreate = resolvedDraftId === null || restoredDraftFailed;
    if (!shouldCreate || createDraft.isPending || createDraft.isSuccess) return;

    logger.info("draft_restore_started", {});
    createDraft.mutate(
      { categorySlug, offeringSlug },
      {
        onSuccess: (created) => {
          void setActiveDraftId(customerId, created.id);
          setResolvedDraftId(created.id);
        },
        onError: (err) => {
          logger.warn("draft_create_failed", { category: (err as ApiError).category ?? "unknown" });
        },
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once per resolvedDraftId transition; createDraft's own identity is stable per render but must not retrigger this effect.
  }, [customerId, resolvedDraftId, restoredDraftFailed, categorySlug, offeringSlug]);

  const activeDraftId = createDraft.data?.id ?? (resolvedDraftId && !restoredDraftFailed ? resolvedDraftId : null);
  const activeDraft = createDraft.data ?? (draft.isSuccess ? draft.data : undefined);

  const isLoading =
    resolvedDraftId === undefined || (resolvedDraftId !== null && draft.isLoading && !createDraft.data) || (createDraft.isPending && !createDraft.data);
  const isError = createDraft.isError && !createDraft.data && resolvedDraftId !== null && draft.isError;

  return { draftId: activeDraftId, draft: activeDraft, isLoading, isError, refetchDraft: draft.refetch };
}
