import React, { useCallback, useMemo, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi, type Job } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import { useAppTheme } from "../context/ThemeContext";
import { groupJobs, type MyWorkGroupKey } from "../lib/ux05/myWork";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

// MODULE-L5-36: rewired from the dead field_ops job list to the real
// service_jobs list (GET /v1/staff/service-jobs). That endpoint has no
// server-side status filter or pagination -- it returns every job assigned
// to the caller in one call -- so tabs filter client-side here instead. No
// service_type/customer_name/address/job_value/SLA fields exist on this
// job shape; only what ServiceJob itself stores is shown.
//
// UX-05 Round 3: "My Work" grouping tabs now use the real, tested
// groupJobs()/classifyJob() (src/lib/ux05/myWork.ts) instead of this
// screen's own separate ACTIVE_STATUSES set -- Current/Today/Upcoming/
// Needs Action/Completed match the same classification Home uses, so a
// job never appears "current" on Home but "upcoming" here.
const TABS: Array<{ key:MyWorkGroupKey; label:string }> = [
  { key:"all",          label:"All"          },
  { key:"current",      label:"Current"      },
  { key:"today",        label:"Today"        },
  { key:"upcoming",     label:"Upcoming"     },
  { key:"needs_action",  label:"Needs Action" },
  { key:"completed",    label:"Completed"    },
];

type Props = { navigation: NativeStackNavigationProp<never> };

export function JobsListScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  const [activeTab, setActiveTab] = useState<MyWorkGroupKey>("all");

  const jobs = useApi(useCallback(() => jobsApi.myJobs(), []));

  const filtered = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    if (activeTab === "all") return all;
    return groupJobs(all)[activeTab];
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
    <View style={[gs.screen, { backgroundColor:colors.bg }]}>
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

function makeStyles(colors: ReturnType<typeof import("../styles/theme").getColors>) {
  return StyleSheet.create({
    tabs:        { flexDirection:"row", backgroundColor:colors.surface, borderBottomWidth:1,
                   borderBottomColor:colors.border, paddingHorizontal:4 },
    tab:         { flex:1, alignItems:"center", paddingVertical:12, borderBottomWidth:2,
                   borderBottomColor:"transparent" },
    tabActive:   { borderBottomColor:colors.brand },
    tabText:     { fontSize:theme.font.size.xs, fontWeight:"600", color:colors.textSecondary },
    tabTextActive:{ color:colors.brand },
    jobCard:     { backgroundColor:colors.surface, borderRadius:theme.radius.lg, padding:14,
                   ...theme.shadow.sm },
    jobTop:      { flexDirection:"row", alignItems:"flex-start", gap:10, marginBottom:6 },
    jobNum:      { fontSize:theme.font.size.base, fontWeight:"700", color:colors.textPrimary },
    service:     { fontSize:theme.font.size.sm, color:colors.textSecondary, marginTop:2 },
    customer:    { fontSize:theme.font.size.sm, color:colors.textSecondary },
    address:     { fontSize:theme.font.size.xs, color:colors.textTertiary, marginTop:3 },
    jobBottom:   { flexDirection:"row", justifyContent:"space-between", marginTop:10 },
    date:        { fontSize:theme.font.size.xs, color:colors.textTertiary },
    value:       { fontSize:theme.font.size.sm, fontWeight:"700", color:colors.successText },
    empty:       { alignItems:"center", paddingTop:80, gap:10 },
    emptyIcon:   { fontSize:48 },
    emptyText:   { fontSize:theme.font.size.base, color:colors.textTertiary },
  });
}
