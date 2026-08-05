import { useCallback, useMemo } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listMyPrivacyRequests, createMyPrivacyRequest, cancelMyPrivacyRequest,
  getMyPrivacyRequest, listMyConsents, withdrawMyConsent, downloadMyExport,
} from "./privacyDataApi";
import { adaptPrivacyRequest, adaptConsentRecord } from "../adapters/privacyData";
import { CreatePrivacyRequestBody } from "../contracts/privacyData";
import { PrivacyRequest } from "../../domain/privacyData";
import { DomainError } from "../../domain/errors";

export type PrivacyRequestDetailResult =
  | { kind: "found"; request: PrivacyRequest }
  | { kind: "unavailable" };

/** Shared privacy query-key factory (spec section 20) -- reused across
 * requests/history/consents so a mutation can invalidate precisely. */
export const privacyQueryKeys = {
  requests: (page: number = 1) => ["customer", "privacy", "requests", page] as const,
  requestsList: () => ["customer", "privacy", "requestsList"] as const,
  request: (requestId: string) => ["customer", "privacy", "request", requestId] as const,
  consents: () => ["customer", "privacy", "consents"] as const,
};

/** Fetches at the real backend's max page size (100) per page (spec
 * section 14) -- for the realistic DPDP request volume of one customer
 * (creation itself is rate-limited to 5/day server-side), this proves a
 * "complete bounded result set" after a single page for the overwhelming
 * majority of accounts, which is exactly the condition the Privacy
 * Requests screen needs before it can safely offer Active/Completed tabs
 * (spec section 10) -- never presenting one partial page as the full
 * Active or Completed list. `isComplete` only ever means "there is
 * definitely no next page," never a guess. */
const LIST_PAGE_SIZE = 100;

export function usePrivacyRequestsListQuery() {
  const query = useInfiniteQuery({
    queryKey: privacyQueryKeys.requestsList(),
    queryFn: async ({ pageParam }: { pageParam: number }) => {
      const res = await listMyPrivacyRequests(pageParam, LIST_PAGE_SIZE);
      return {
        requests: res.data.requests.map(adaptPrivacyRequest),
        meta: res.data.meta,
      };
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.meta.page < lastPage.meta.total_pages ? lastPage.meta.page + 1 : undefined,
  });

  useFocusEffect(
    useCallback(() => {
      query.refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []),
  );

  const items = useMemo(() => {
    const seen = new Set<string>();
    const out: PrivacyRequest[] = [];
    for (const page of query.data?.pages ?? []) {
      for (const item of page.requests) {
        if (seen.has(item.id)) continue;
        seen.add(item.id);
        out.push(item);
      }
    }
    return out;
  }, [query.data]);

  const total = query.data?.pages[0]?.meta.total ?? 0;
  const isComplete = !query.hasNextPage;

  return {
    items, total, isComplete,
    isPending: query.isPending,
    isError: query.isError,
    isRefetching: query.isRefetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    refetch: query.refetch,
  };
}

export function usePrivacyRequestsQuery(page: number = 1) {
  return useQuery({
    queryKey: privacyQueryKeys.requests(page),
    queryFn: async () => {
      const res = await listMyPrivacyRequests(page);
      return {
        requests: res.data.requests.map(adaptPrivacyRequest),
        meta: res.data.meta,
      };
    },
  });
}

/** Route params only ever carry `requestId` (spec section 2) -- this hook
 * is the sole source of truth for the detail screen; a route param is
 * never trusted as a complete request object. Missing and foreign request
 * IDs both hit `NOT_FOUND` (identical shape, see
 * `customer_router.get_my_request`'s ownership-scoped lookup) and collapse
 * to the same "unavailable" result here -- the screen never learns whether
 * a foreign request actually exists (spec section 13/14). */
export function usePrivacyRequestDetailQuery(requestId: string) {
  const query = useQuery({
    queryKey: privacyQueryKeys.request(requestId),
    queryFn: async (): Promise<PrivacyRequestDetailResult> => {
      try {
        const res = await getMyPrivacyRequest(requestId);
        return { kind: "found", request: adaptPrivacyRequest(res.data) };
      } catch (err) {
        if (err instanceof DomainError && err.httpStatus === 404) {
          return { kind: "unavailable" };
        }
        throw err;
      }
    },
  });

  useFocusEffect(
    useCallback(() => {
      query.refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [requestId]),
  );

  return query;
}

function invalidateAllPrivacyRequestQueries(
  queryClient: ReturnType<typeof useQueryClient>, requestId?: string,
) {
  queryClient.invalidateQueries({ queryKey: ["customer", "privacy", "requests"] });
  queryClient.invalidateQueries({ queryKey: privacyQueryKeys.requestsList() });
  if (requestId) {
    queryClient.invalidateQueries({ queryKey: privacyQueryKeys.request(requestId) });
  }
}

export function useCreatePrivacyRequestMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreatePrivacyRequestBody) => createMyPrivacyRequest(body),
    onSuccess: () => invalidateAllPrivacyRequestQueries(queryClient),
  });
}

export function useCancelPrivacyRequestMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: string) => cancelMyPrivacyRequest(requestId),
    onSuccess: (_data, requestId) => invalidateAllPrivacyRequestQueries(queryClient, requestId),
  });
}

export function useConsentsQuery() {
  return useQuery({
    queryKey: privacyQueryKeys.consents(),
    queryFn: async () => {
      const res = await listMyConsents();
      return res.data.items.map(adaptConsentRecord);
    },
  });
}

export function useWithdrawConsentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ consentType, reason }: { consentType: string; reason?: string }) =>
      withdrawMyConsent(consentType, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: privacyQueryKeys.consents() });
    },
  });
}

export function useDownloadExportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ exportId }: { exportId: string; requestId?: string }) => downloadMyExport(exportId),
    onSuccess: (_data, { requestId }) => invalidateAllPrivacyRequestQueries(queryClient, requestId),
  });
}
