import React, { useState } from "react";
import { View, FlatList, RefreshControl, ActivityIndicator, Pressable, AccessibilityInfo } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState, ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  useNotificationsListQuery, useUnreadNotificationCountQuery,
  useMarkNotificationReadMutation, useMarkAllNotificationsReadMutation,
} from "../../api/notifications/useNotificationsQueries";
import { CustomerNotification } from "../../domain/notification";
import {
  groupNotificationsByDay, resolveNotificationVisual, formatUnreadCount,
} from "../../domain/notificationPresentation";
import { resolveCustomerNotificationType } from "../../domain/notificationTypeMapping";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "Notifications">;
type Filter = "all" | "unread";

function formatTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatEarlierDate(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/**
 * Real REST-backed in-app notification list (`app/engines/
 * platform_notifications/customer_router.py`). Not a push phase -- no
 * `expo-notifications` usage, no permission prompts, no device tokens
 * (spec section 2/19). Destinations are limited to the explicit allowlist
 * in `domain/notificationDestination.ts`; every other notification is
 * safe but non-interactive.
 */
export function NotificationCenterScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [filter, setFilter] = useState<Filter>("all");
  const query = useNotificationsListQuery(filter);
  const unreadCountQuery = useUnreadNotificationCountQuery();
  const markReadMutation = useMarkNotificationReadMutation();
  const markAllReadMutation = useMarkAllNotificationsReadMutation();
  const offline = isOffline();

  const unreadCount = unreadCountQuery.data ?? 0;

  function openNotification(notification: CustomerNotification) {
    const wasUnread = notification.readStatus === "unread";
    if (wasUnread && !markReadMutation.isPending) {
      markReadMutation.mutate(notification.id);
    }
    if (notification.destination?.kind === "booking") {
      navigation.navigate("BookingDetails", { bookingId: notification.destination.bookingId });
    } else if (notification.destination?.kind === "supportRequest") {
      navigation.navigate("SupportRequestDetails", { requestId: notification.destination.requestId });
    }
    // No destination -- the row was still marked read above (when the
    // backend permits it), but there is nowhere safe to navigate.
  }

  async function handleMarkAllRead() {
    if (markAllReadMutation.isPending) return;
    await markAllReadMutation.mutateAsync();
    AccessibilityInfo.announceForAccessibility("All notifications marked as read.");
  }

  if (query.isPending) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} showMarkAllRead={false} onMarkAllRead={handleMarkAllRead} />
        <LoadingState label="Loading your notifications…" />
      </AppScreen>
    );
  }

  if (offline && query.items.length === 0) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} showMarkAllRead={false} onMarkAllRead={handleMarkAllRead} />
        <OfflineBanner />
        <ErrorState
          title="Notifications can't be loaded"
          message="Reconnect to see your notifications."
          actionLabel="Try again" onAction={() => query.refetch()}
        />
      </AppScreen>
    );
  }

  if (query.isError && query.items.length === 0) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} showMarkAllRead={false} onMarkAllRead={handleMarkAllRead} />
        <ErrorState
          title="Something went wrong" message="We couldn't load your notifications."
          actionLabel="Try again" onAction={() => query.refetch()}
        />
      </AppScreen>
    );
  }

  const groups = groupNotificationsByDay(query.items);
  const isCaughtUp = !query.hasNextPage && query.items.length > 0;

  const rows: Array<
    | { kind: "group"; label: string }
    | { kind: "item"; notification: CustomerNotification }
  > = [];
  for (const group of groups) {
    rows.push({ kind: "group", label: group.label });
    for (const n of group.items) rows.push({ kind: "item", notification: n });
  }

  return (
    <AppScreen edges={["top", "bottom"]} style={{ paddingHorizontal: 0 }}>
      <View style={{ paddingHorizontal: theme.layout.screenHorizontalPadding }}>
        <Header
          navigation={navigation}
          showMarkAllRead={unreadCount > 0 && !markAllReadMutation.isPending}
          onMarkAllRead={handleMarkAllRead}
        />

        {offline ? <OfflineBanner /> : null}
        {!offline && query.isError ? (
          <AppText variant="bodySmall" color="danger" style={{ marginBottom: theme.spacing.xs }}>
            We couldn't refresh your notifications. Showing your last known list.
          </AppText>
        ) : null}

        <View style={{ marginBottom: theme.spacing.base }}>
          <AppText variant="title" accessibilityRole="header">Stay updated</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
            <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>
              Booking and support updates in one place.
            </AppText>
            {unreadCount > 0 ? (
              <View
                style={{
                  paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
                  borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusWarningSurface,
                }}
              >
                <AppText variant="labelStrong" style={{ color: theme.colors.statusWarning }}>
                  {formatUnreadCount(unreadCount)}
                </AppText>
              </View>
            ) : null}
          </View>
        </View>

        <View
          accessibilityRole="tablist"
          style={{
            flexDirection: "row", backgroundColor: theme.colors.surfaceInteractive,
            borderRadius: theme.radiusUsage.button, padding: 4, marginBottom: theme.spacing.base,
          }}
        >
          <FilterTab label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
          <FilterTab label="Unread" selected={filter === "unread"} onPress={() => setFilter("unread")} />
        </View>
      </View>

      {rows.length === 0 ? (
        filter === "unread" ? (
          <EmptyState
            icon="checkmark-circle-outline"
            title="You're all caught up"
            message="There are no unread notifications."
          />
        ) : (
          <EmptyState
            icon="notifications-outline"
            title="No notifications yet"
            message="Booking and support updates will appear here."
          />
        )
      ) : (
        <FlatList
          data={rows}
          keyExtractor={(row, i) => (row.kind === "group" ? `group-${row.label}-${i}` : row.notification.id)}
          contentContainerStyle={{ paddingHorizontal: theme.layout.screenHorizontalPadding, paddingBottom: theme.spacing.xxl }}
          refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
          onEndReachedThreshold={0.4}
          onEndReached={() => {
            if (query.hasNextPage && !query.isFetchingNextPage) query.fetchNextPage();
          }}
          renderItem={({ item }) =>
            item.kind === "group" ? (
              <AppText variant="labelStrong" color="secondary" style={{ marginTop: theme.spacing.base, marginBottom: theme.spacing.xs }}>
                {item.label}
              </AppText>
            ) : (
              <NotificationRow notification={item.notification} onPress={() => openNotification(item.notification)} />
            )
          }
          ListFooterComponent={
            <View style={{ gap: theme.spacing.sm, marginTop: theme.spacing.sm, alignItems: "center" }}>
              {query.isFetchingNextPage ? <ActivityIndicator color={theme.colors.brandPrimaryStrong} /> : null}
              {isCaughtUp ? (
                <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, paddingVertical: theme.spacing.base }}>
                  <Icon name="checkmark-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
                  <AppText variant="bodySmall" color="tertiary">You're all caught up</AppText>
                </View>
              ) : null}
            </View>
          }
        />
      )}
    </AppScreen>
  );
}

function Header({
  navigation, showMarkAllRead, onMarkAllRead,
}: { navigation: Nav; showMarkAllRead: boolean; onMarkAllRead: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
      <AppText variant="headingSmall" accessibilityRole="header" style={{ flex: 1, marginLeft: theme.spacing.xs }}>
        Notifications
      </AppText>
      {showMarkAllRead ? (
        <AppText
          variant="labelStrong" color="link" onPress={onMarkAllRead}
          accessibilityRole="button" accessibilityLabel="Mark all notifications as read"
        >
          Mark all read
        </AppText>
      ) : null}
    </View>
  );
}

function FilterTab({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected }}
      accessibilityLabel={label}
      style={{
        flex: 1, minHeight: 44, alignItems: "center", justifyContent: "center",
        borderRadius: theme.radiusUsage.button,
        backgroundColor: selected ? theme.colors.brandPrimary : "transparent",
      }}
    >
      <AppText variant="labelStrong" style={{ color: selected ? theme.colors.brandOnPrimary : theme.colors.textSecondary }}>
        {label}
      </AppText>
    </Pressable>
  );
}

function NotificationRow({ notification, onPress }: { notification: CustomerNotification; onPress: () => void }) {
  const { theme } = useTheme();
  const visual = resolveNotificationVisual(notification);
  const typePresentation = resolveCustomerNotificationType(notification.type);
  const interactive = notification.destination !== null;
  const created = toDisplayDate(notification.createdAt);
  const isToday = new Date().toDateString() === created.toDateString();

  return (
    <Pressable
      onPress={interactive ? onPress : undefined}
      accessibilityRole={interactive ? "button" : undefined}
      accessibilityLabel={`${visual.accessibilityStateLabel}. ${notification.title}. ${notification.body}`}
      style={{
        flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start",
        paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.sm,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: visual.unread ? theme.colors.statusWarningSurface : "transparent",
        borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle,
        minHeight: 44,
      }}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
          backgroundColor: theme.colors.surfaceInteractive,
        }}
      >
        <Icon name={typePresentation.icon} size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          {visual.unread ? (
            <View
              accessibilityElementsHidden
              style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary }}
            />
          ) : null}
          <AppText variant={visual.titleWeight === "strong" ? "bodyStrong" : "bodySmall"} style={{ flex: 1 }}>
            {notification.title}
          </AppText>
          <AppText variant="caption" color="tertiary">
            {isToday ? formatTime(notification.createdAt) : formatEarlierDate(notification.createdAt)}
          </AppText>
        </View>
        <AppText variant="bodySmall" color="secondary">{notification.body}</AppText>
      </View>
      {interactive ? (
        <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
      ) : null}
    </Pressable>
  );
}
