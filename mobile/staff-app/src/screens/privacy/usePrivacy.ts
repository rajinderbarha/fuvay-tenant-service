import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/privacy/privacyApi";
import { PrivacyRequestType } from "../../services/privacy/types";
import { AppError } from "../../services/api/types";

const SUMMARY_KEY = ["privacy-summary"] as const;
const CONSENTS_KEY = ["privacy-consents"] as const;

/** Privacy & Data (Phase X). Reuses the SAME canonical global compliance
 * system every other subject (customer/tenant) uses -- this hook never
 * computes privacy status locally, and never claims "Saved"/"Submitted"
 * before the backend confirms it. */
export function usePrivacy() {
  const queryClient = useQueryClient();
  const [mutatingPurpose, setMutatingPurpose] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const summary = useQuery({
    queryKey: SUMMARY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getSummary(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const consents = useQuery({
    queryKey: CONSENTS_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getConsents(signal);
      if (!result.ok) throw result.error;
      return result.data.consents;
    },
  });

  const toggleConsent = useCallback(async (purposeCode: string, enabled: boolean) => {
    setMutatingPurpose(purposeCode);
    setMutationError(null);
    queryClient.setQueryData(CONSENTS_KEY, (prev: typeof consents.data) =>
      prev ? prev.map(c => c.purpose_code === purposeCode ? { ...c, enabled } : c) : prev);
    const result = await api.updateConsent(purposeCode, enabled);
    setMutatingPurpose(null);
    if (!result.ok) {
      setMutationError(result.error);
      await queryClient.invalidateQueries({ queryKey: CONSENTS_KEY });
      return { ok: false as const };
    }
    await queryClient.invalidateQueries({ queryKey: CONSENTS_KEY });
    return { ok: true as const };
  }, [queryClient, consents.data]);

  const submitRequest = useCallback(async (requestType: PrivacyRequestType, reason: string, details?: string, isAccountClosure?: boolean) => {
    const result = await api.submitRequest({ requestType, reason, details, isAccountClosure });
    if (result.ok) {
      await queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
      return { ok: true as const, requestId: result.data.request_id };
    }
    return { ok: false as const, error: result.error };
  }, [queryClient]);

  return {
    summary: summary.data, summaryLoading: summary.isLoading, summaryError: summary.error as AppError | null,
    summaryIsError: summary.isError, refetchSummary: summary.refetch,
    consents: consents.data ?? [], consentsLoading: consents.isLoading,
    mutatingPurpose, mutationError, toggleConsent,
    submitRequest,
  };
}
