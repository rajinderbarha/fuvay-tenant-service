import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listJobQuotes, getQuote, approveQuote, declineQuote } from "./customerQuoteApi";
import { adaptCustomerQuote } from "../adapters/customerQuote";
import { CustomerQuote } from "../../domain/customerQuote";
import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../idempotency/idempotencyStore";

export type CurrentQuoteResult =
  | { kind: "found"; quote: CustomerQuote }
  | { kind: "none" };

const jobQuoteKey = (jobId: string) => ["customer-quote", "job", jobId] as const;
const quoteDetailKey = (quoteId: string) => ["customer-quote", "detail", quoteId] as const;

/** Resolves the job's current quote (if any) and its full customer-safe
 * detail in one hook -- `kind: "none"` is a real, honest state (inspection
 * not yet submitted / no quote required), never an error. Refresh-on-focus
 * is already provided by the parent `BookingDetailsScreen`'s own booking
 * query (which this hook's `enabled` flag is derived from) -- a second,
 * independent `useFocusEffect` here would double-fetch on every focus. */
export function useCurrentQuoteQuery(jobId: string, enabled: boolean) {
  return useQuery({
    queryKey: jobQuoteKey(jobId),
    queryFn: async (): Promise<CurrentQuoteResult> => {
      const list = await listJobQuotes(jobId);
      const current = list.data[0];
      if (!current) return { kind: "none" };
      const detail = await getQuote(current.id);
      return { kind: "found", quote: adaptCustomerQuote(detail.data) };
    },
    enabled,
  });
}

export function useApproveQuoteMutation(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (quoteId: string) => {
      const scope = `quote-approve:${quoteId}`;
      const key = await getOrCreateIdempotencyKey(scope);
      const res = await approveQuote(quoteId, key);
      await clearIdempotencyKey(scope);
      return adaptCustomerQuote(res.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobQuoteKey(jobId) });
    },
  });
}

export function useDeclineQuoteMutation(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ quoteId, reason }: { quoteId: string; reason: string }) => {
      const res = await declineQuote(quoteId, reason);
      return adaptCustomerQuote(res.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobQuoteKey(jobId) });
    },
  });
}
