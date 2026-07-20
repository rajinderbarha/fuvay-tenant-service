import React, { useCallback, useMemo } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { notificationsApi, type StaffNotification } from "../lib/api";
import { Skeleton } from "../components/Skeleton";
import { NotificationCard } from "../components/ux05/NotificationCard";
import { theme, gs } from "../styles/theme";
import { useAppTheme } from "../context/ThemeContext";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { NotificationView } from "../types/ux05";

// MODULE-L5-37: the staff app had no notification surface at all -- server-
// side job-assignment/booking notifications (MODULE-L5-25 etc.) were never
// fetched or shown, so a technician only learned of a new job by polling the
// Jobs tab. This screen lists /v1/staff/notifications, marks them read, and
// deep-links via action_url where the app has a matching route.
//
// UX-05 Round 6: converted to reactive theme colors (useAppTheme()) and now
// renders rows via the real NotificationCard component (built in Round 2,
// unused until now) instead of a duplicate inline renderer -- closes both
// the "static light-only" and "built but not wired" gaps flagged in
// known-limitations.md.
type Props = { navigation: NativeStackNavigationProp<never> };

const SEVERITY_TO_PRIORITY: Record<string, NotificationView["priority"]> = {
  critical: "high", warning: "medium", info: "low", success: "low",
};

export function NotificationsScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  const notifs = useApi(useCallback(() => notificationsApi.list(50), []));
  const markAll = useAction(useCallback(() => notificationsApi.markAllRead(), []));
  const markOne = useAction(useCallback((id:string) => notificationsApi.markRead(id), []));

  // The app only knows how to route job-assignment notifications to a job
  // detail; anything else just marks read in place (no fabricated routes).
  async function open(n:StaffNotification) {
    if (n.read_status !== "read") { await markOne.execute(n.id); }
    // Assignment notifications carry source_record_type "service_jobs" +
    // the ServiceJob id (see home_service_assignment/service.py) -- deep-link
    // straight into the real job detail rewired in MODULE-L5-36.
    if (n.source_record_type === "service_jobs" && n.source_record_id) {
      navigation.navigate("JobDetail" as never, { jobId:n.source_record_id } as never);
      return;
    }
    notifs.refetch();
  }

  async function handleMarkAll() {
    const r = await markAll.execute();
    if (r) notifs.refetch();
  }

  function renderItem({ item:n }: { item:StaffNotification }) {
    const view: NotificationView = {
      meta: { readiness: "production_ready" },
      notification: n,
      priority: SEVERITY_TO_PRIORITY[n.severity] ?? "low",
    };
    return <NotificationCard item={view} onPress={() => open(n)} />;
  }

  const items = notifs.data?.items ?? [];
  const hasUnread = items.some(n => n.read_status !== "read");

  return (
    <View style={[gs.screen, { backgroundColor:colors.bg }]}>
      {hasUnread && (
        <TouchableOpacity style={s.markAllBtn} onPress={handleMarkAll} disabled={markAll.loading}
          accessibilityRole="button" accessibilityLabel="Mark all notifications as read">
          <Text style={s.markAllText}>{markAll.loading ? "…" : "Mark all as read"}</Text>
        </TouchableOpacity>
      )}
      {notifs.loading ? (
        <View style={{ padding:theme.spacing.base, gap:12 }}>
          {[...Array(6)].map((_,i) => <Skeleton key={i} height={70} />)}
        </View>
      ) : (
        <FlatList
          data={items}
          renderItem={renderItem}
          keyExtractor={n => n.id}
          onRefresh={notifs.refetch}
          refreshing={notifs.loading}
          ItemSeparatorComponent={() => <View style={[gs.sep, { backgroundColor:colors.border }]} />}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:80, gap:10 }}>
              <Text style={{ fontSize:48 }}>🔔</Text>
              <Text style={{ fontSize:theme.font.size.base, color:colors.textTertiary }}>
                No notifications yet
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

function makeStyles(colors: ReturnType<typeof import("../styles/theme").getColors>) {
  return StyleSheet.create({
    markAllBtn:  { alignSelf:"flex-end", paddingHorizontal:theme.spacing.base, paddingVertical:10 },
    markAllText: { fontSize:theme.font.size.sm, fontWeight:"600", color:colors.brand },
  });
}
