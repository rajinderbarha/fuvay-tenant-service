import React, { useCallback } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { notificationsApi, type StaffNotification } from "../lib/api";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

// MODULE-L5-37: the staff app had no notification surface at all -- server-
// side job-assignment/booking notifications (MODULE-L5-25 etc.) were never
// fetched or shown, so a technician only learned of a new job by polling the
// Jobs tab. This screen lists /v1/staff/notifications, marks them read, and
// deep-links via action_url where the app has a matching route.
type Props = { navigation: NativeStackNavigationProp<never> };

const SEVERITY_COLOR: Record<string, string> = {
  info: theme.colors.brand, warning: theme.colors.warning,
  critical: theme.colors.danger, success: theme.colors.success,
};

export function NotificationsScreen({ navigation }: Props) {
  const notifs = useApi(useCallback(() => notificationsApi.list(50), []));
  const markAll = useAction(useCallback(() => notificationsApi.markAllRead(), []));
  const markOne = useAction(useCallback((id:string) => notificationsApi.markRead(id), []));

  const fmt = (d:string) => new Date(d).toLocaleString("en-IN",{ day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" });

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
    const unread = n.read_status !== "read";
    const accent = SEVERITY_COLOR[n.severity] ?? theme.colors.brand;
    return (
      <TouchableOpacity style={[s.row, unread && s.rowUnread]} activeOpacity={0.85}
        onPress={() => open(n)}>
        <View style={[s.dot, { backgroundColor: unread ? accent : "transparent", borderColor:accent }]} />
        <View style={{ flex:1 }}>
          <Text style={[s.title, unread && s.titleUnread]}>{n.title}</Text>
          {n.body && <Text style={s.body} numberOfLines={2}>{n.body}</Text>}
          <Text style={s.time}>{fmt(n.created_at)}</Text>
        </View>
      </TouchableOpacity>
    );
  }

  const items = notifs.data?.items ?? [];
  const hasUnread = items.some(n => n.read_status !== "read");

  return (
    <View style={gs.screen}>
      {hasUnread && (
        <TouchableOpacity style={s.markAllBtn} onPress={handleMarkAll} disabled={markAll.loading}>
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
          ItemSeparatorComponent={() => <View style={gs.sep} />}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:80, gap:10 }}>
              <Text style={{ fontSize:48 }}>🔔</Text>
              <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textTertiary }}>
                No notifications yet
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  markAllBtn:  { alignSelf:"flex-end", paddingHorizontal:theme.spacing.base, paddingVertical:10 },
  markAllText: { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.brand },
  row:         { flexDirection:"row", alignItems:"flex-start", gap:12, padding:14, backgroundColor:theme.colors.surface },
  rowUnread:   { backgroundColor:theme.colors.surfaceSunken },
  dot:         { width:10, height:10, borderRadius:5, borderWidth:1.5, marginTop:5 },
  title:       { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  titleUnread: { fontWeight:"800" },
  body:        { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:3 },
  time:        { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:4 },
});
