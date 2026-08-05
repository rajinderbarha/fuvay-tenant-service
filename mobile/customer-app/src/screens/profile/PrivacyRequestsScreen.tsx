import React, { useState } from "react";
import { View, FlatList, RefreshControl, ActivityIndicator, Pressable } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppBadge } from "../../components/AppBadge";
import { AppIconButton } from "../../components/AppIconButton";
import { Icon } from "../../components/Icon";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState, ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { usePrivacyRequestsListQuery } from "../../api/privacyData/usePrivacyDataQueries";
import {
  resolvePrivacyRequestType, resolvePrivacyRequestStatus, isTerminalPrivacyStatus,
} from "../../domain/privacyRequestPresentation";
import { PrivacyRequest } from "../../domain/privacyData";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { isOffline } from "../../api/networkState";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "PrivacyRequests">;
type Filter = "all" | "active" | "completed";

function formatDate(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/**
 * Read-only privacy request tracking (`GET /v1/me/compliance/requests`,
 * real offset/limit pagination + real `meta.total`). Active/Completed
 * tabs only render once `isComplete` proves the fully-loaded set is
 * genuinely complete -- never a guess from one partial page (spec section
 * 10). No request creation, cancellation, download or consent mutation
 * happens on this screen.
 */
export function PrivacyRequestsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [filter, setFilter] = useState<Filter>("all");
  const query = usePrivacyRequestsListQuery();
  const offline = isOffline();

  if (query.isPending) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} />
        <LoadingState label="Loading your privacy requests…" />
      </AppScreen>
    );
  }

  if (offline && query.items.length === 0) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} />
        <OfflineBanner />
        <ErrorState
          title="Requests can't be loaded" message="Reconnect to see your privacy requests."
          actionLabel="Try again" onAction={() => query.refetch()}
        />
      </AppScreen>
    );
  }

  if (query.isError && query.items.length === 0) {
    return (
      <AppScreen edges={["top", "bottom"]}>
        <Header navigation={navigation} />
        <ErrorState
          title="Something went wrong" message="We couldn't load your privacy requests."
          actionLabel="Try again" onAction={() => query.refetch()}
        />
      </AppScreen>
    );
  }

  const showFilters = query.isComplete;
  const active = query.items.filter(r => !isTerminalPrivacyStatus(r.status));
  const completed = query.items.filter(r => isTerminalPrivacyStatus(r.status));

  const visible = !showFilters || filter === "all" ? query.items : filter === "active" ? active : completed;

  const rows: Array<
    | { kind: "section"; label: string }
    | { kind: "item"; request: PrivacyRequest }
  > = [];
  if (showFilters && filter === "all") {
    if (active.length) {
      rows.push({ kind: "section", label: "Active" });
      for (const r of active) rows.push({ kind: "item", request: r });
    }
    if (completed.length) {
      rows.push({ kind: "section", label: "Completed" });
      for (const r of completed) rows.push({ kind: "item", request: r });
    }
  } else {
    for (const r of visible) rows.push({ kind: "item", request: r });
  }

  return (
    <AppScreen edges={["top", "bottom"]} style={{ paddingHorizontal: 0 }}>
      <View style={{ paddingHorizontal: theme.layout.screenHorizontalPadding }}>
        <Header navigation={navigation} />
        {offline ? <OfflineBanner /> : null}
        {!offline && query.isError ? (
          <AppText variant="bodySmall" color="danger" style={{ marginBottom: theme.spacing.xs }}>
            We couldn't refresh your requests. Showing your last known list.
          </AppText>
        ) : null}

        <View style={{ marginBottom: theme.spacing.base }}>
          <AppText variant="title" accessibilityRole="header">Track your requests</AppText>
          <AppText variant="bodySmall" color="secondary">View the progress of privacy requests submitted to Fuvay.</AppText>
        </View>

        {showFilters ? (
          <View
            accessibilityRole="tablist"
            style={{
              flexDirection: "row", backgroundColor: theme.colors.surfaceInteractive,
              borderRadius: theme.radiusUsage.button, padding: 4, marginBottom: theme.spacing.base,
            }}
          >
            <FilterTab label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
            <FilterTab label="Active" selected={filter === "active"} onPress={() => setFilter("active")} />
            <FilterTab label="Completed" selected={filter === "completed"} onPress={() => setFilter("completed")} />
          </View>
        ) : null}
      </View>

      {rows.length === 0 ? (
        <View style={{ paddingHorizontal: theme.layout.screenHorizontalPadding }}>
          {filter === "active" ? (
            <EmptyState icon="checkmark-circle-outline" title="No active requests" message="Your completed request history is still available." />
          ) : filter === "completed" ? (
            <EmptyState icon="document-text-outline" title="No completed requests yet" />
          ) : (
            <EmptyState
              icon="shield-outline" title="No privacy requests yet"
              message="Requests you submit will appear here."
              actionLabel="Back to Privacy & data" onAction={() => navigation.goBack()}
            />
          )}
        </View>
      ) : (
        <FlatList
          data={rows}
          keyExtractor={(row, i) => (row.kind === "section" ? `section-${row.label}` : row.request.id + i)}
          contentContainerStyle={{ paddingHorizontal: theme.layout.screenHorizontalPadding, paddingBottom: theme.spacing.xxl, gap: theme.spacing.sm }}
          refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => query.refetch()} />}
          onEndReachedThreshold={0.4}
          onEndReached={() => {
            if (query.hasNextPage && !query.isFetchingNextPage) query.fetchNextPage();
          }}
          renderItem={({ item }) =>
            item.kind === "section" ? (
              <AppText variant="labelStrong" color="secondary" style={{ marginTop: theme.spacing.sm }}>{item.label}</AppText>
            ) : (
              <PrivacyRequestRow
                request={item.request}
                onPress={() => navigation.navigate("PrivacyRequestDetails", { requestId: item.request.id })}
              />
            )
          }
          ListFooterComponent={
            <View style={{ gap: theme.spacing.base, marginTop: theme.spacing.sm }}>
              {query.isFetchingNextPage ? <ActivityIndicator color={theme.colors.brandPrimaryStrong} /> : null}
              <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive }}>
                <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.textSecondary} decorative />
                <View style={{ flex: 1 }}>
                  <AppText variant="bodyStrong">Requests are private</AppText>
                  <AppText variant="bodySmall" color="secondary">Only you can view the requests linked to your account.</AppText>
                </View>
              </View>
              <AppText
                variant="labelStrong" color="link" align="center" onPress={() => navigation.goBack()}
                accessibilityRole="button" accessibilityLabel="Back to Privacy and data"
              >
                Back to Privacy & data
              </AppText>
            </View>
          }
        />
      )}
    </AppScreen>
  );
}

function Header({ navigation }: { navigation: Nav }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm }}>
      <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
      <AppText variant="headingSmall" accessibilityRole="header" style={{ flex: 1, marginLeft: theme.spacing.xs }}>
        Privacy requests
      </AppText>
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

function PrivacyRequestRow({ request, onPress }: { request: PrivacyRequest; onPress: () => void }) {
  const { theme } = useTheme();
  const typeLabel = resolvePrivacyRequestType(request.requestType);
  const status = resolvePrivacyRequestStatus(request.status);
  const submitted = request.submittedAt ?? request.createdAt;
  const updated = request.updatedAt;
  const reference = request.requestNumber || null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${typeLabel}, ${status.title}${reference ? `, Request ${reference}` : ""}. View details.`}
      style={{
        borderLeftWidth: 3, borderLeftColor: theme.colors.brandPrimary,
        borderRadius: theme.radiusUsage.card, overflow: "hidden",
      }}
    >
      <AppCard style={{ gap: theme.spacing.xs }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <View
            style={{
              width: 40, height: 40, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.surfaceInteractive,
            }}
          >
            <Icon name={requestTypeIcon(request.requestType)} size="standard" color={theme.colors.textSecondary} decorative />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <AppText variant="caption" color="tertiary">{typeLabel.toUpperCase()}</AppText>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <AppText variant="bodyStrong">{typeLabel}</AppText>
              <AppBadge label={status.title} tone={status.tone} />
            </View>
            {reference ? <AppText variant="caption" color="secondary">Request {reference}</AppText> : null}
          </View>
        </View>
        <View style={{ flexDirection: "row", gap: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.xs }}>
          {submitted ? (
            <View>
              <AppText variant="caption" color="tertiary">Submitted</AppText>
              <AppText variant="bodySmall">{formatDate(submitted)}</AppText>
            </View>
          ) : null}
          {request.completedAt ? (
            <View>
              <AppText variant="caption" color="tertiary">Completed</AppText>
              <AppText variant="bodySmall">{formatDate(request.completedAt)}</AppText>
            </View>
          ) : updated ? (
            <View>
              <AppText variant="caption" color="tertiary">Updated</AppText>
              <AppText variant="bodySmall">{formatDate(updated)}</AppText>
            </View>
          ) : null}
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <AppText variant="labelStrong" color="link">View details</AppText>
          <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
        </View>
      </AppCard>
    </Pressable>
  );
}

function requestTypeIcon(requestType: string): React.ComponentProps<typeof Icon>["name"] {
  switch (requestType) {
    case "data_export": return "download-outline";
    case "data_correction": return "create-outline";
    case "right_to_erasure": return "person-remove-outline";
    case "consent_withdrawal":
    case "consent_update": return "checkmark-done-outline";
    case "processing_objection": return "hand-left-outline";
    case "grievance": return "alert-circle-outline";
    default: return "document-text-outline";
  }
}
