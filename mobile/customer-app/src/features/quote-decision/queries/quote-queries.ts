import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { quoteApi } from "../api/quote-api";
import { parseQuoteList, parseQuoteDetail } from "../domain/quote-schema";
import { getRequestLocale, getRequestTenantId } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";

export const quoteQueryKeys = {
  jobQuotes: (jobId: string, locale: string, tenantId: string | undefined) => ["quoteDecision", "jobQuotes", jobId, locale, tenantId ?? "no-tenant"] as const,
  detail: (quoteId: string, locale: string, tenantId: string | undefined) => ["quoteDecision", "detail", quoteId, locale, tenantId ?? "no-tenant"] as const,
};

export function useJobQuotes(jobId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: quoteQueryKeys.jobQuotes(jobId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await quoteApi.getJobQuotes(jobId as string, { signal });
      const parsed = parseQuoteList(response);
      if (!parsed) {
        logger.warn("quote_list_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Quote list response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: Boolean(jobId),
    staleTime: 0,
    retry: 1,
  });
}

export function useQuoteDetail(quoteId: string | null) {
  const locale = getRequestLocale();
  const tenantId = getRequestTenantId();

  return useQuery({
    queryKey: quoteQueryKeys.detail(quoteId ?? "none", locale, tenantId),
    queryFn: async ({ signal }) => {
      const response = await quoteApi.getQuote(quoteId as string, { signal });
      const parsed = parseQuoteDetail(response);
      if (!parsed) {
        logger.warn("quote_detail_load_failed", { reason: "validation" });
        throw new ApiError({ category: "validation_error", message: "Quote detail response did not match the expected shape." });
      }
      return parsed;
    },
    enabled: Boolean(quoteId),
    staleTime: 0,
    retry: 1,
  });
}

/** Invalidates every cache this decision affects: the job's quote list/detail, and both booking-detail queries (`booking-confirmation` and `bookings`) whose `job.status`/`job_status` change as a server-side side effect of the decision (contract-matrix.md's job/booking status side-effects table). */
function useInvalidateAfterDecision() {
  const queryClient = useQueryClient();
  return (jobId: string) => {
    void queryClient.invalidateQueries({ queryKey: ["quoteDecision", "jobQuotes", jobId] });
    void queryClient.invalidateQueries({ queryKey: ["quoteDecision", "detail"] });
    void queryClient.invalidateQueries({ queryKey: ["booking", "detail"] });
    void queryClient.invalidateQueries({ queryKey: ["bookings", "detail"] });
    void queryClient.invalidateQueries({ queryKey: ["bookings", "tracking"] });
  };
}

/** The approve response itself is not parsed/rendered — this mutation exists only to trigger the real state change; the invalidated `useQuoteDetail`/`useJobQuotes` refetch is the single source of truth for the resulting quote shape, avoiding a second, divergent parse path for the same data. */
export function useApproveQuote(jobId: string) {
  const invalidate = useInvalidateAfterDecision();
  return useMutation<void, ApiError, { quoteId: string; idempotencyKey: string }>({
    mutationFn: async ({ quoteId, idempotencyKey }) => {
      logger.info("quote_approve_started", {});
      await quoteApi.approveQuote(quoteId, idempotencyKey);
    },
    onSuccess: () => {
      logger.info("quote_approve_succeeded", {});
      invalidate(jobId);
    },
    onError: () => {
      logger.warn("quote_approve_failed", {});
    },
  });
}

export function useRejectQuote(jobId: string) {
  const invalidate = useInvalidateAfterDecision();
  return useMutation<unknown, ApiError, { quoteId: string; reason: string }>({
    mutationFn: async ({ quoteId, reason }) => {
      logger.info("quote_reject_started", {});
      return quoteApi.rejectQuote(quoteId, reason);
    },
    onSuccess: () => {
      logger.info("quote_reject_succeeded", {});
      invalidate(jobId);
    },
    onError: () => {
      logger.warn("quote_reject_failed", {});
    },
  });
}

export function useRequestQuoteRevision(jobId: string) {
  const invalidate = useInvalidateAfterDecision();
  return useMutation<unknown, ApiError, { quoteId: string; reason: string }>({
    mutationFn: async ({ quoteId, reason }) => {
      logger.info("quote_revision_request_started", {});
      return quoteApi.requestRevision(quoteId, reason);
    },
    onSuccess: () => {
      logger.info("quote_revision_request_succeeded", {});
      invalidate(jobId);
    },
    onError: () => {
      logger.warn("quote_revision_request_failed", {});
    },
  });
}
