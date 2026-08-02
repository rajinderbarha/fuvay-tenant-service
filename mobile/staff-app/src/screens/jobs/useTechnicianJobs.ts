import { useMemo } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useSession } from "../../navigation/session/SessionProvider";
import { queryKeys } from "../../state/queries/queryKeys";
import * as jobsApi from "../../services/jobs/jobsApi";
import { JobsView } from "../../services/jobs/types";

export interface UseTechnicianJobsInput {
  view: JobsView;
  search: string;
  workflowStatus?: string;
  actionRequired?: boolean;
}

/**
 * Jobs directory data (Phase I spec sections 7, 12, 13). Cursor pagination
 * via TanStack Query's useInfiniteQuery -- stable query key includes
 * view/search/filters (spec section 13), so switching tabs or applying a
 * filter never shows stale results and never needs manual cache-busting.
 */
export function useTechnicianJobs(input: UseTechnicianJobsInput) {
  const { accessContext } = useSession();
  const tenantId = accessContext.tenantId ?? "";
  const technicianId = accessContext.technicianId ?? "";

  const params = useMemo(() => ({
    view: input.view, search: input.search || undefined,
    workflowStatus: input.workflowStatus, actionRequired: input.actionRequired,
  }), [input.view, input.search, input.workflowStatus, input.actionRequired]);

  const queryKey = queryKeys.jobs.list(tenantId, technicianId, params as Record<string, unknown>);

  const query = useInfiniteQuery({
    queryKey,
    queryFn: async ({ pageParam, signal }) => {
      const result = await jobsApi.getMobileJobs({ ...params, cursor: pageParam as string | undefined }, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: lastPage => (lastPage.has_more ? lastPage.next_cursor ?? undefined : undefined),
    enabled: Boolean(tenantId && technicianId),
  });

  const items = useMemo(() => {
    const seen = new Set<string>();
    const deduped = [];
    for (const page of query.data?.pages ?? []) {
      for (const item of page.results) {
        if (seen.has(item.job_id)) continue;
        seen.add(item.job_id);
        deduped.push(item);
      }
    }
    return deduped;
  }, [query.data]);

  const countsByView = query.data?.pages[0]?.counts_by_view;

  return {
    items,
    countsByView,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as { safeMessage?: string } | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    fetchNextPage: query.fetchNextPage,
    hasNextPage: query.hasNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
  };
}
