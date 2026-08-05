import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { LoginActivityHeader } from "../../components/login-activity/LoginActivityHeader";
import { LoginActivitySummaryPanel } from "../../components/login-activity/LoginActivitySummaryPanel";
import { LoginActivityFilterTabs } from "../../components/login-activity/LoginActivityFilterTabs";
import { LoginActivityCard } from "../../components/login-activity/LoginActivityCard";
import { SecurityRemediationCard } from "../../components/login-activity/SecurityRemediationCard";
import { useLoginActivityQuery } from "../../api/customerSecurity/useLoginActivityQuery";
import { LoginActivityEvent, LoginActivityFilter } from "../../domain/customerSecurity";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { ServerTimestamp } from "../../domain/dates";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "LoginActivity">;

function dayGroupFor(occurredAt: ServerTimestamp): string {
  const date = new Date(occurredAt);
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diffDays = Math.round((startOfDay(now) - startOfDay(date)) / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Earlier";
}

function groupByDay(events: LoginActivityEvent[]): { title: string; events: LoginActivityEvent[] }[] {
  const order = ["Today", "Yesterday", "Earlier"];
  const groups = new Map<string, LoginActivityEvent[]>();
  for (const e of events) {
    const key = dayGroupFor(e.occurredAt);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(e);
  }
  return order.filter(k => groups.has(k)).map(title => ({ title, events: groups.get(title)! }));
}

/**
 * Opened from Security -> "Login activity". Every event shown is real,
 * sourced from the canonical `LoginEvent` table via `GET /v1/auth/me/
 * login-activity` -- no synthetic events, no client-side generation.
 */
export function LoginActivityScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [filter, setFilter] = useState<LoginActivityFilter>("all");
  const query = useLoginActivityQuery(filter);
  const offline = isOffline();

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading login activity…" />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your login activity." actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  const events = (query.data?.pages ?? []).flatMap(p => p.events);
  const groups = groupByDay(events);

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {offline && query.data ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <LoginActivityHeader onBack={() => navigation.goBack()} />
        <LoginActivitySummaryPanel />
        <LoginActivityFilterTabs value={filter} onChange={setFilter} />

        {events.length === 0 ? (
          <View style={{ alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.xl }}>
            <AppText variant="bodyStrong">No login activity available</AppText>
            <AppText variant="bodySmall" color="secondary" align="center">New sign-in activity will appear here when available.</AppText>
          </View>
        ) : (
          groups.map(group => (
            <View key={group.title} style={{ gap: theme.spacing.xs }}>
              <AppText variant="labelStrong" color="secondary">{group.title}</AppText>
              <View style={{ gap: theme.spacing.sm }}>
                {group.events.map(event => (
                  <LoginActivityCard key={event.eventId} event={event} />
                ))}
              </View>
            </View>
          ))
        )}

        {query.hasNextPage ? (
          <AppButton
            label="Load more" tone="secondary" onPress={async () => { await query.fetchNextPage(); }}
            loading={query.isFetchingNextPage} fullWidth
          />
        ) : null}

        <SecurityRemediationCard
          onReviewSessions={() => navigation.navigate("ManageSessions")}
          onChangePassword={() => navigation.navigate("Security")}
        />

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <AppText variant="caption" color="tertiary" align="center">Login history is read-only and cannot be deleted.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
