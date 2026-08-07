import { useCallback, useMemo } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useInfiniteQuery } from "@tanstack/react-query";
import { listMyBookings } from "./customerBookingsApi";
import { adaptBookingListPage } from "../adapters/bookingList";
import { BookingListCounts } from "../../domain/bookingList";
import { BookingListFilter } from "../../domain/bookingFilters";
import { bookingQueryKeys } from "./bookingQueryKeys";

const PAGE_SIZE = 20;

/**
 * CLOSURE (2026-08-01): replaces the prior "fetch every booking, classify
 * client-side" strategy. `bucket` now filters server-side, and every
 * response carries authoritative `counts` for all three tabs -- so
 * switching tabs never re-derives a count from a partial fetch, and a
 * customer with a large history no longer pays for a full-list scan just
 * to render "Active {n}". True incremental pagination via
 * `useInfiniteQuery` (real "load more", not a single giant fetch).
 */
export function useCustomerBookingsListQuery(
  bucket: BookingListFilter,
  search?: string,
  statusFilter?: string | null,
) {
  // Normalised once so " ac " and "ac" share a cache entry rather than
  // refetching the same result under two keys.
  const q = search?.trim() ? search.trim() : undefined;
  const status = statusFilter ?? undefined;
  const query = useInfiniteQuery({
    queryKey: bookingQueryKeys.list({ bucket, status, q }),
    queryFn: async ({ pageParam }: { pageParam: number }) => {
      const res = await listMyBookings(bucket, PAGE_SIZE, pageParam, q, status);
      return adaptBookingListPage(res.data);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      if (lastPage.items.length === 0 || loaded >= lastPage.total) return undefined;
      return loaded;
    },
  });

  useFocusEffect(
    useCallback(() => {
      query.refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [bucket, q]),
  );

  const items = useMemo(() => query.data?.pages.flatMap(p => p.items) ?? [], [query.data]);
  const counts: BookingListCounts = query.data?.pages[query.data.pages.length - 1]?.counts
    ?? { active: 0, completed: 0, all: 0 };

  return {
    items,
    counts,
    isPending: query.isPending,
    isError: query.isError,
    isRefetching: query.isRefetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    refetch: query.refetch,
    dataUpdatedAt: query.dataUpdatedAt,
  };
}
