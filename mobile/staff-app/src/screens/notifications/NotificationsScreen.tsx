import React, { useCallback, useMemo, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Heading } from "../../design-system/components/typography/Heading";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState, EmptyState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { TertiaryButton } from "../../design-system/components/actions/Buttons";
import { NotificationRow } from "./components/NotificationRow";
import { useNotifications } from "./useNotifications";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { NotificationFilter, NotificationCategory, NotificationItemDTO, DayGroup } from "../../services/notifications/types";

const FILTERS: { key: NotificationFilter; label: string }[] = [
  { key: "all", label: "All" }, { key: "unread", label: "Unread" }, { key: "action_required", label: "Action needed" },
];
const CATEGORIES: { key: NotificationCategory; label: string; icon: any }[] = [
  { key: "jobs", label: "Jobs", icon: "briefcase-outline" },
  { key: "schedule", label: "Schedule", icon: "calendar-outline" },
  { key: "payments", label: "Payments", icon: "cash-outline" },
  { key: "account", label: "Account", icon: "person-outline" },
];
const GROUP_LABEL: Record<DayGroup, string> = { today: "Today", yesterday: "Yesterday", earlier: "Earlier" };

/**
 * Technician Notifications Center (Phase Q). A real event inbox over the
 * canonical InAppNotification model -- opening the tab never marks
 * everything read; only opening/tapping one row marks that one.
 */
export function NotificationsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<any>();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [filter, setFilter] = useState<NotificationFilter>("all");
  const [category, setCategory] = useState<NotificationCategory | null>(null);

  const { data, isLoading, isError, error, isRefetching, refetch, mutating, mutationError, markRead, markAllRead } = useNotifications(filter, category);

  const openDestination = useCallback(async (item: NotificationItemDTO) => {
    if (!item.is_read) await markRead(item.id);
    const dest = item.destination;
    if (!dest) return;
    if (dest.type === "job" && dest.id) {
      navigation.getParent()?.navigate("JobExecutionStack", { screen: "JobDetail", params: { jobId: dest.id } });
    } else if (dest.type === "schedule") {
      navigation.navigate("Schedule");
    } else if (dest.type === "security") {
      navigation.navigate("Profile");
    }
    // Unknown/unauthorized destination types are silently ignored -- never
    // an arbitrary navigation (spec section 5).
  }, [markRead, navigation]);

  const grouped = useMemo(() => {
    const groups: Record<DayGroup, NotificationItemDTO[]> = { today: [], yesterday: [], earlier: [] };
    (data?.items ?? []).forEach(item => groups[item.day_group].push(item));
    return groups;
  }, [data]);

  if (isLoading) {
    return (
      <SafeAreaScreen style={{ padding: theme.spacing.lg }}>
        <Skeleton width="50%" height={24} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={40} radius={theme.radiusUsage.card} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load notifications" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  const counts = data?.counts ?? { all: 0, unread: 0, action_required: 0 };
  const hasAny = (data?.items.length ?? 0) > 0;

  return (
    <SafeAreaScreen style={{ flex: 1, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.base }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.base }}>
        <View>
          <Heading level="large">Notifications</Heading>
          <AppText color="secondary">Updates that need your attention</AppText>
        </View>
        <IconButton icon="ellipsis-vertical" accessibilityLabel="More options" onPress={() => {}} />
      </View>

      <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginBottom: theme.spacing.sm }} accessibilityRole="tablist">
        {FILTERS.map(f => {
          const selected = filter === f.key;
          const count = f.key === "all" ? counts.all : f.key === "unread" ? counts.unread : counts.action_required;
          return (
            <View
              key={f.key}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              accessibilityLabel={`${f.label}, ${count}`}
              onTouchEnd={() => setFilter(f.key)}
              style={{
                flex: 1, alignItems: "center", paddingVertical: theme.spacing.sm, borderRadius: theme.radiusUsage.button,
                backgroundColor: selected ? theme.colors.brandPrimary : theme.colors.surfaceInteractive,
              }}
            >
              <AppText variant="bodyStrong" style={{ color: selected ? theme.colors.brandOnPrimary : theme.colors.textPrimary }}>{f.label} {count}</AppText>
            </View>
          );
        })}
      </View>

      <ScrollView
        horizontal showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: theme.spacing.sm, marginBottom: theme.spacing.base }}
        style={{ flexGrow: 0 }}
      >
        {CATEGORIES.map(c => {
          const selected = category === c.key;
          return (
            <View
              key={c.key}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              accessibilityLabel={c.label}
              onTouchEnd={() => setCategory(selected ? null : c.key)}
              style={{
                paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm, borderRadius: theme.radiusUsage.statusPill,
                borderWidth: 1, borderColor: selected ? theme.colors.brandPrimary : theme.colors.borderDefault,
                backgroundColor: selected ? theme.colors.brandPrimaryMuted : "transparent",
              }}
            >
              <AppText variant="bodySmall" color={selected ? "primary" : "secondary"}>{c.label}</AppText>
            </View>
          );
        })}
      </ScrollView>

      <ScrollView
        contentContainerStyle={{ paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached notifications." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        {!hasAny ? (
          <EmptyState icon="notifications-outline" title={filter === "all" ? "No notifications" : filter === "unread" ? "No unread notifications" : "Nothing needs action"} message="You're all caught up." />
        ) : (
          (["today", "yesterday", "earlier"] as DayGroup[]).map(group => grouped[group].length > 0 ? (
            <Section key={group}>
              <AppText variant="label" color="tertiary" style={{ marginBottom: theme.spacing.xs }}>{GROUP_LABEL[group]}</AppText>
              <Card padding="base">
                {grouped[group].map((item, i) => (
                  <View key={item.id} style={i > 0 ? { borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle } : undefined}>
                    <NotificationRow item={item} onPress={() => openDestination(item)} />
                  </View>
                ))}
              </Card>
            </Section>
          ) : null)
        )}

        {hasAny ? (
          <TertiaryButton label="Mark all as read" onPress={() => { void markAllRead(); }} loading={mutating} fullWidth />
        ) : null}
      </ScrollView>
    </SafeAreaScreen>
  );
}
