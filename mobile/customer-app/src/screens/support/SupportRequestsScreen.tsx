import React, { useState } from "react";
import { View, FlatList, RefreshControl, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppBadge } from "../../components/AppBadge";
import { AppIconButton } from "../../components/AppIconButton";
import { AppButton } from "../../components/AppButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { Icon } from "../../components/Icon";
import { OfflineBanner } from "../../components/OfflineBanner";
import { useSupportRequestsListQuery } from "../../api/supportRequests/useSupportRequestsQueries";
import { resolveSupportRequestPresentation, resolveSupportRequestStage, SupportRequestStage } from "../../domain/supportRequestPresentation";
import { SupportRequest } from "../../domain/supportRequests";
import { formatRelativeServerTime, ServerTimestamp } from "../../domain/dates";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "SupportRequests">;
type Tab = "active" | "resolved" | "all";

const TAB_LABEL: Record<Tab, string> = { active: "Active", resolved: "Resolved", all: "All" };

/**
 * Real history of the customer's own complaint/support-request engine
 * (`GET /v1/customer/complaints`) -- this IS "My support requests" (no
 * separate ticket system exists, confirmed during the Help & Support Hub
 * audit). The backend has no offset/cursor pagination (a hardcoded
 * `.limit(100)` with no total count) and no group status filter, only an
 * exact-status filter -- so Active/Resolved/All are classified client-side
 * from a single full fetch via `resolveSupportRequestStage`, never from a
 * partial page (spec section 4/9).
 */
export function SupportRequestsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const query = useSupportRequestsListQuery();
  const [tab, setTab] = useState<Tab>("active");
  const offline = isOffline();

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your requests…" />
      </AppScreen>
    );
  }

  if (offline && !query.data) {
    return (
      <AppScreen>
        <OfflineBanner />
        <ErrorState title="You're offline" message="Connect to the internet to view your support requests." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your requests." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  const all = query.data ?? [];
  const visible = tab === "all" ? all : all.filter(r => resolveSupportRequestStage(r.status) === tab);
  const emptyCopy: Record<Tab, { title: string; message: string }> = {
    active: { title: "No active requests", message: "You don't have any support requests in progress." },
    resolved: { title: "No resolved requests", message: "Requests you've resolved will appear here." },
    all: { title: "No support requests yet", message: "When you contact support, your requests will appear here." },
  };

  return (
    <AppScreen edges={["top", "bottom"]}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, padding: theme.layout.screenHorizontalPadding, paddingBottom: 0 }}>
        <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" accessibilityRole="header">My support requests</AppText>
          <AppText variant="bodySmall" color="secondary">Track help you've requested</AppText>
        </View>
        <AppIconButton
          name="refresh" onPress={() => query.refetch()} accessibilityLabel="Refresh"
          disabled={query.isRefetching}
        />
      </View>

      <View style={{ padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.base }}>
        {offline && all.length > 0 ? <OfflineBanner /> : null}
        {query.isError && all.length > 0 ? (
          <AppText variant="bodySmall" color="danger">We couldn't refresh your requests. Showing the last known list.</AppText>
        ) : null}

        <AppCard style={{ gap: theme.spacing.sm }}>
          <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "center" }}>
            <Icon name="add-circle-outline" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Need more help?</AppText>
              <AppText variant="bodySmall" color="secondary">Create a secure support request.</AppText>
            </View>
            <AppButton
              label="New request" tone="primary" size="compact"
              onPress={() => navigation.navigate("CreateSupportRequest", { source: "support_requests" })}
            />
          </View>
        </AppCard>

        <View style={{ flexDirection: "row", backgroundColor: theme.colors.surfaceInteractive, borderRadius: theme.radiusUsage.statusPill, padding: 2 }}>
          {(["active", "resolved", "all"] as Tab[]).map(t => (
            <Pressable
              key={t}
              accessibilityRole="tab" accessibilityState={{ selected: tab === t }}
              accessibilityLabel={TAB_LABEL[t]}
              onPress={() => setTab(t)}
              style={{
                flex: 1, alignItems: "center", paddingVertical: theme.spacing.xs,
                borderRadius: theme.radiusUsage.statusPill,
                backgroundColor: tab === t ? theme.colors.surfaceDefault : "transparent",
              }}
            >
              <AppText variant="labelStrong" color={tab === t ? "primary" : "secondary"}>{TAB_LABEL[t]}</AppText>
            </Pressable>
          ))}
        </View>
      </View>

      {visible.length === 0 ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: theme.layout.screenHorizontalPadding, gap: theme.spacing.sm }}>
          <Icon name="chatbox-ellipses-outline" size="feature" color={theme.colors.textSecondary} decorative />
          <AppText variant="bodyStrong" align="center">{emptyCopy[tab].title}</AppText>
          <AppText variant="bodySmall" color="secondary" align="center">{emptyCopy[tab].message}</AppText>
        </View>
      ) : (
        <FlatList
          data={visible}
          keyExtractor={item => item.id}
          contentContainerStyle={{ padding: theme.layout.screenHorizontalPadding, paddingTop: 0, gap: theme.spacing.sm }}
          refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
          ListFooterComponent={
            <AppText variant="caption" color="tertiary" align="center" style={{ paddingTop: theme.spacing.sm }}>
              Pull down to check for updates.
            </AppText>
          }
          renderItem={({ item }: { item: SupportRequest }) => (
            <SupportRequestRow
              item={item}
              onPress={() => navigation.navigate("SupportRequestDetails", { requestId: item.id })}
              onOpenBooking={item.bookingId ? () => navigation.navigate("BookingDetails", { bookingId: item.bookingId as string }) : undefined}
            />
          )}
        />
      )}
    </AppScreen>
  );
}

function SupportRequestRow({ item, onPress, onOpenBooking }: {
  item: SupportRequest; onPress: () => void; onOpenBooking?: () => void;
}) {
  const { theme } = useTheme();
  const presentation = resolveSupportRequestPresentation(item);
  const updated = item.updatedAt ?? item.createdAt;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${presentation.typeLabel}, ${presentation.statusLabel}`}
      onPress={onPress}
    >
      <AppCard style={{ gap: theme.spacing.xs }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <Icon name="chatbox-ellipses-outline" size="standard" color={theme.colors.textSecondary} decorative />
          <View style={{ flex: 1, gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong">{presentation.typeLabel}</AppText>
            <AppText variant="caption" color="secondary">Request {item.complaintNumber}</AppText>
            <View style={{ alignSelf: "flex-start" }}>
              <AppBadge label={presentation.statusLabel} tone={presentation.tone} />
            </View>
          </View>
          <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
        </View>

        {onOpenBooking ? (
          <Pressable
            accessibilityRole="button" accessibilityLabel="View linked booking"
            onPress={onOpenBooking}
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
          >
            <Icon name="link-outline" size="compact" color={theme.colors.textSecondary} decorative />
            <AppText variant="caption" color="link">Linked to a booking</AppText>
          </Pressable>
        ) : null}

        {updated ? (
          <AppText variant="caption" color="tertiary">Updated {formatRelativeServerTime(updated as ServerTimestamp)}</AppText>
        ) : null}
      </AppCard>
    </Pressable>
  );
}
