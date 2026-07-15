import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { jobsApi, notificationsApi } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { StatCard } from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

type Props = { navigation: NativeStackNavigationProp<never> };

// MODULE-L5-36: rewired from the dead field_ops job list to the real
// service_jobs list. That list endpoint returns only job_number/status/
// city/scheduled_date/timestamps -- no customer name/phone/address or SLA
// timer fields (ServiceJob has neither; those require a separate per-job
// detail fetch that joins the booking). No per-item detail fetch is done
// here to keep the home screen a single cheap list call.
const ACTIVE_STATUSES = [
  "accepted","on_the_way","reached_site","inspection_started",
  "inspection_done","quote_required","service_started","work_done",
];

export function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const jobs     = useApi(useCallback(() => jobsApi.myJobs(), []));
  // MODULE-L5-37: surface the unread-notification count as a bell badge so a
  // technician actually sees a newly-assigned job instead of having to poll.
  const unread   = useApi(useCallback(() => notificationsApi.unreadCount(), []));
  const unreadCount = unread.data?.unread_count ?? 0;

  const allJobs  = jobs.data?.jobs ?? [];
  const active   = allJobs.find(j => ACTIVE_STATUSES.includes(j.status));
  const today    = allJobs.filter(j => new Date(j.created_at).toDateString() === new Date().toDateString());
  const done     = today.filter(j => j.status === "completed").length;
  const greeting = new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 17 ? "Good afternoon" : "Good evening";

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.greeting}>{greeting},</Text>
          <Text style={s.name}>{user?.full_name?.split(" ")[0] ?? "Staff"} 👋</Text>
        </View>
        <View style={{ flexDirection:"row", alignItems:"center", gap:12 }}>
          <TouchableOpacity onPress={() => navigation.navigate("Notifications" as never)} style={s.bell}>
            <Text style={{ fontSize:22 }}>🔔</Text>
            {unreadCount > 0 && (
              <View style={s.badge}>
                <Text style={s.badgeText}>{unreadCount > 9 ? "9+" : unreadCount}</Text>
              </View>
            )}
          </TouchableOpacity>
          <View style={s.avatar}>
            <Text style={s.avatarText}>{user?.full_name?.[0] ?? "S"}</Text>
          </View>
        </View>
      </View>

      {/* Stats row */}
      <View style={s.statsRow}>
        <StatCard label="Today" value={String(today.length)} sub="jobs assigned" />
        <StatCard label="Done"  value={String(done)}         sub="completed" accent={theme.colors.success} />
        <StatCard label="Rating" value={user?.rating ? `★ ${user.rating.toFixed(1)}` : "—"} sub="avg score" accent={theme.colors.warning} />
      </View>

      {/* Active job */}
      <Text style={gs.label}>Active Job</Text>
      {jobs.loading ? <Skeleton height={120} style={{ marginBottom:16 }} />
      : active ? (
        <TouchableOpacity style={[gs.card, s.activeCard]}
          onPress={() => navigation.navigate("JobDetail" as never, { jobId:active.id } as never)}
          activeOpacity={0.9}>
          <View style={[gs.row, { justifyContent:"space-between", marginBottom:10 }]}>
            <Text style={s.jobNumber}>{active.job_number}</Text>
            <JobStatusBadge status={active.status} />
          </View>
          {active.city && <Text style={s.address}>📍 {active.city}{active.zipcode ? `, ${active.zipcode}` : ""}</Text>}
          {active.scheduled_date && (
            <Text style={s.address}>🗓 {active.scheduled_date}{active.scheduled_time_window ? ` · ${active.scheduled_time_window}` : ""}</Text>
          )}
          <View style={s.actionRow}>
            <View style={[s.actionBtn, s.actionBtnPrimary]}>
              <Text style={[s.actionText, { color:"#fff" }]}>View Job →</Text>
            </View>
          </View>
        </TouchableOpacity>
      ) : (
        <View style={[gs.card, s.noActive]}>
          <Text style={s.noActiveIcon}>✅</Text>
          <Text style={s.noActiveText}>No active job right now</Text>
          <Text style={s.noActiveSub}>Check your Jobs tab for upcoming assignments</Text>
        </View>
      )}

      {/* Upcoming jobs */}
      <Text style={[gs.label, { marginTop:8 }]}>Upcoming Today</Text>
      {jobs.loading ? (
        <>{[...Array(3)].map((_,i) => <Skeleton key={i} height={64} style={{ marginBottom:8 }} />)}</>
      ) : today.filter(j => j.status === "assigned" || j.status === "accepted").map(j => (
        <TouchableOpacity key={j.id} style={[gs.card, s.jobRow]}
          onPress={() => navigation.navigate("JobDetail" as never, { jobId:j.id } as never)}
          activeOpacity={0.85}>
          <View style={{ flex:1 }}>
            <Text style={s.jobNumber}>{j.job_number}</Text>
            <Text style={s.customer}>{j.city ?? "—"}</Text>
          </View>
          <JobStatusBadge status={j.status} size="sm" />
        </TouchableOpacity>
      ))}

      {!jobs.loading && today.filter(j=>["assigned","accepted"].includes(j.status)).length===0 && (
        <View style={[gs.card, { alignItems:"center", paddingVertical:24 }]}>
          <Text style={s.noActiveSub}>No more jobs scheduled for today</Text>
        </View>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  header:       { flexDirection:"row", justifyContent:"space-between", alignItems:"center",
                  paddingTop:8, paddingBottom:4 },
  greeting:     { fontSize:theme.font.size.base, color:theme.colors.textSecondary },
  name:         { fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.textPrimary },
  avatar:       { width:44, height:44, borderRadius:22, backgroundColor:theme.colors.brand,
                  alignItems:"center", justifyContent:"center" },
  avatarText:   { fontSize:theme.font.size.xl, fontWeight:"700", color:"#fff" },
  bell:         { width:44, height:44, alignItems:"center", justifyContent:"center" },
  badge:        { position:"absolute", top:4, right:4, minWidth:18, height:18, borderRadius:9,
                  backgroundColor:theme.colors.danger, alignItems:"center", justifyContent:"center", paddingHorizontal:4 },
  badgeText:    { fontSize:9, fontWeight:"800", color:"#fff" },
  statsRow:     { flexDirection:"row", gap:10 },
  activeCard:   { borderLeftWidth:4, borderLeftColor:theme.colors.accent, paddingLeft:14 },
  jobNumber:    { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  serviceType:  { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary, marginBottom:3 },
  customer:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  address:      { fontSize:theme.font.size.sm, color:theme.colors.textTertiary, marginTop:4 },
  actionRow:    { flexDirection:"row", gap:10, marginTop:14 },
  actionBtn:    { flex:1, height:38, borderRadius:theme.radius.md, borderWidth:1,
                  borderColor:theme.colors.border, alignItems:"center", justifyContent:"center" },
  actionBtnPrimary:{ backgroundColor:theme.colors.brand, borderColor:"transparent" },
  actionText:   { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
  noActive:     { alignItems:"center", paddingVertical:32, gap:6 },
  noActiveIcon: { fontSize:36 },
  noActiveText: { fontSize:theme.font.size.lg, fontWeight:"600", color:theme.colors.textPrimary },
  noActiveSub:  { fontSize:theme.font.size.sm, color:theme.colors.textTertiary },
  jobRow:       { flexDirection:"row", alignItems:"center", gap:12 },
});
