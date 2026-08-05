import { useCallback, useMemo } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listMyNotifications, getMyUnreadNotificationCount,
  markMyNotificationRead, markAllMyNotificationsRead,
} from "./notificationsApi";
import { adaptNotification } from "../adapters/notification";
import { queryKeys } from "../queryKeys";

const PAGE_SIZE = 30;

/**
 * Real server-side filtering (`read_status=unread`) -- never a client-side
 * simulation over one loaded page (spec section 6). Separate cache entries
 * per filter so switching tabs never flashes the other tab's stale data.
 */
export function useNotificationsListQuery(filter: "all" | "unread") {
  const query = useInfiniteQuery({
    queryKey: queryKeys.notifications.list(filter),
    queryFn: async ({ pageParam }: { pageParam: number }) => {
      const res = await listMyNotifications(filter === "unread" ? "unread" : undefined, PAGE_SIZE, pageParam);
      return { items: res.data.items.map(adaptNotification), total: res.data.total };
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
    }, [filter]),
  );

  // De-duplicated across pages by id -- an item that shifts pages between
  // an initial fetch and a subsequent load-more (e.g. after a mark-read
  // changes its `read_status` under the Unread filter) can never appear
  // twice in the rendered list.
  const items = useMemo(() => {
    const seen = new Set<string>();
    const out: ReturnType<typeof adaptNotification>[] = [];
    for (const page of query.data?.pages ?? []) {
      for (const item of page.items) {
        if (seen.has(item.id)) continue;
        seen.add(item.id);
        out.push(item);
      }
    }
    return out;
  }, [query.data]);

  const total = query.data?.pages[query.data.pages.length - 1]?.total ?? 0;

  return {
    items,
    total,
    isPending: query.isPending,
    isError: query.isError,
    isRefetching: query.isRefetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    refetch: query.refetch,
  };
}

/** Canonical unread-count source -- the same `NotificationService.
 * get_unread_count()` call that already backs Customer Home's
 * `unread_notification_count`, so this screen's header badge and Home's
 * bell dot are never allowed to disagree for more than one refetch. */
export function useUnreadNotificationCountQuery() {
  return useQuery({
    queryKey: queryKeys.notifications.unreadCount(),
    queryFn: async () => (await getMyUnreadNotificationCount()).data.unread_count,
  });
}

function invalidateNotificationCaches(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: queryKeys.notifications.list("all") });
  queryClient.invalidateQueries({ queryKey: queryKeys.notifications.list("unread") });
  queryClient.invalidateQueries({ queryKey: queryKeys.notifications.unreadCount() });
  // Home renders its own `unread_notification_count` from its aggregate
  // query -- invalidated broadly (not by exact zipcode key) so it refetches
  // regardless of the customer's currently-selected address.
  queryClient.invalidateQueries({ queryKey: ["home"] });
}

export function useMarkNotificationReadMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => markMyNotificationRead(notificationId),
    onSuccess: () => invalidateNotificationCaches(queryClient),
  });
}

/** Gated by the screen on `total unread > 0` and "not already pending" --
 * this hook only performs the real bulk mutation, never a client-side loop
 * over the currently loaded page (spec section 14). */
export function useMarkAllNotificationsReadMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => markAllMyNotificationsRead(),
    onSuccess: () => invalidateNotificationCaches(queryClient),
  });
}
