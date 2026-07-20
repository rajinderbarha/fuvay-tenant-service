import { useMemo, useState } from "react";
import { useBookingsList } from "../queries/bookings-queries";
import { groupForStatus } from "../domain/booking-group";
import type { BookingStatusGroup } from "../domain/booking-status-registry";

/**
 * Composes the real, server-paginated infinite list with a client-side
 * Active/Past segmented filter (CUSTOMER-L5-12 §11) — the real
 * `GET /v1/customer/bookings` endpoint has no status/date filter param at
 * all (contract-matrix.md), so grouping is applied over whatever pages
 * have been loaded so far via the same real pagination, not a separate
 * fabricated server-side filter.
 */
export function useBookingsListView() {
  const [activeGroup, setActiveGroup] = useState<BookingStatusGroup>("active");
  const query = useBookingsList();

  const allItems = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);
  const visibleItems = useMemo(() => allItems.filter((item) => groupForStatus(item.status) === activeGroup), [allItems, activeGroup]);

  return {
    activeGroup,
    setActiveGroup,
    items: visibleItems,
    isLoading: query.isPending,
    isError: query.isError,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: Boolean(query.hasNextPage),
    loadMore: () => {
      if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
    },
    refresh: () => query.refetch(),
    isRefreshing: query.isRefetching && !query.isFetchingNextPage,
  };
}
