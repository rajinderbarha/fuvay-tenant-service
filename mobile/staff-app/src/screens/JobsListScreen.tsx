import React, { useCallback, useMemo, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi, type Job } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

// MODULE-L5-36: rewired from the dead field_ops job list to the real
// service_jobs list (GET /v1/staff/service-jobs). That endpoint has no
// server-side status filter or pagination -- it returns every job assigned
// to the caller in one call -- so tabs filter client-side here instead. No
// service_type/customer_name/address/job_value/SLA fields exist on this
// job shape; only what ServiceJob itself stores is shown.
const TABS = [
  { key:"",           label:"All"       },
  { key:"assigned",   label:"Assigned"  },
  { key:"active",     label:"Active"    },
  { key:"completed",  label:"Completed" },
  { key:"cancelled",  label:"Cancelled" },
] as const;

const ACTIVE_STATUSES = new Set([
  "accepted","on_the_way","reached_site","inspection_started",
  "inspection_done","quote_required","service_started","work_done",
]);

type Props = { navigation: NativeStackNavigationProp<never> };

export function JobsListScreen({ navigation }: Props) {
  const [activeTab, setActiveTab] = useState("");

  const jobs = useApi(useCallback(() => jobsApi.myJobs(), []));

  const filtered = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    if (!activeTab) return all;
    if (activeTab === "active") return all.filter(j => ACTIVE_STATUSES.has(j.status));
    return all.filter(j => j.status === activeTab);
  }, [jobs.data, activeTab]);

  const fmt = (d:string) => new Date(d).toLocaleDateString("en-IN",{ day:"numeric", month:"short" });

  function renderJob({ item:j }: { item:Job }) {
    return (
      <TouchableOpacity style={s.jobCard} activeOpacity={0.85}
        onPress={() => navigation.navigate("JobDetail" as never, { jobId:j.id } as never)}>
        <View style={s.jobTop}>
          <View style={{ flex:1 }}>
            <Text style={s.jobNum}>{j.job_number}</Text>
            {j.city && <Text style={s.service}>{j.city}{j.zipcode ? `, ${j.zipcode}` : ""}</Text>}
          </View>
          <JobStatusBadge status={j.status} size="sm" />
        </View>
        {j.scheduled_date && (
          <Text style={s.address}>🗓 {j.scheduled_date}{j.scheduled_time_window ? ` · ${j.scheduled_time_window}` : ""}</Text>
        )}
        <View style={s.jobBottom}>
          <Text style={s.date}>{fmt(j.created_at)}</Text>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <View style={gs.screen}>
      {/* Tab bar */}
      <View style={s.tabs}>
        {TABS.map(t => (
          <TouchableOpacity key={t.key} onPress={() => setActiveTab(t.key)}
            style={[s.tab, activeTab===t.key && s.tabActive]}>
            <Text style={[s.tabText, activeTab===t.key && s.tabTextActive]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {jobs.loading ? (
        <View style={{ padding:theme.spacing.base, gap:12 }}>
          {[...Array(5)].map((_,i) => <Skeleton key={i} height={100} />)}
        </View>
      ) : (
        <FlatList
          data={filtered}
          renderItem={renderJob}
          keyExtractor={j => j.id}
          contentContainerStyle={{ padding:theme.spacing.base, gap:10, paddingBottom:32 }}
          onRefresh={jobs.refetch}
          refreshing={jobs.loading}
          ListEmptyComponent={
            <View style={s.empty}>
              <Text style={s.emptyIcon}>📋</Text>
              <Text style={s.emptyText}>No jobs {activeTab ? `with status "${activeTab}"` : "assigned"}</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  tabs:        { flexDirection:"row", backgroundColor:theme.colors.surface, borderBottomWidth:1,
                 borderBottomColor:theme.colors.border, paddingHorizontal:4 },
  tab:         { flex:1, alignItems:"center", paddingVertical:12, borderBottomWidth:2,
                 borderBottomColor:"transparent" },
  tabActive:   { borderBottomColor:theme.colors.brand },
  tabText:     { fontSize:theme.font.size.xs, fontWeight:"600", color:theme.colors.textSecondary },
  tabTextActive:{ color:theme.colors.brand },
  jobCard:     { backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg, padding:14,
                 ...theme.shadow.sm },
  jobTop:      { flexDirection:"row", alignItems:"flex-start", gap:10, marginBottom:6 },
  jobNum:      { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  service:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  customer:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  address:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:3 },
  jobBottom:   { flexDirection:"row", justifyContent:"space-between", marginTop:10 },
  date:        { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  value:       { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.successText },
  empty:       { alignItems:"center", paddingTop:80, gap:10 },
  emptyIcon:   { fontSize:48 },
  emptyText:   { fontSize:theme.font.size.base, color:theme.colors.textTertiary },
});
