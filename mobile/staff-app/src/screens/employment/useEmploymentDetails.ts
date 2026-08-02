import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/employment/employmentApi";
import { CorrectionFieldKey } from "../../services/employment/types";
import { AppError } from "../../services/api/types";

const QUERY_KEY = ["employment-details"] as const;
const CORRECTIONS_KEY = ["employment-corrections"] as const;

/** Employment Details (Phase S). Read-only projection over the canonical
 * ProviderTeamMember -- this hook never accepts a mutation payload for
 * tenant-controlled fields, only submits a correction REQUEST that a tenant
 * manager must separately decide on. */
export function useEmploymentDetails() {
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getEmploymentDetails(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const corrections = useQuery({
    queryKey: CORRECTIONS_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.listCorrectionRequests(signal);
      if (!result.ok) throw result.error;
      return result.data.requests;
    },
    enabled: !!query.data?.allowed_actions.request_correction,
  });

  const submitCorrection = useCallback(async (fieldKey: CorrectionFieldKey, requestedValue: string, reason: string) => {
    if (submitting) return { ok: false as const };
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.submitCorrectionRequest({ fieldKey, requestedValue, reason });
      if (!result.ok) {
        setSubmitError(result.error);
        return { ok: false as const, error: result.error };
      }
      await queryClient.invalidateQueries({ queryKey: CORRECTIONS_KEY });
      return { ok: true as const };
    } finally {
      setSubmitting(false);
    }
  }, [submitting, queryClient]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    corrections: corrections.data ?? [],
    correctionsLoading: corrections.isLoading,
    submitting, submitError,
    submitCorrection,
  };
}
