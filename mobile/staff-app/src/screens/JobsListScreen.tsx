import React, { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi, type Job } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { SlaTimer } from "../components/SlaTimer";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

const TABS = [
  { key:"",           label:"All"         },
  { key:"assigned",   label:"Assigned"    },
  { key:"in_progress",label:"In Progress" },
  { key:"completed",  label:"Completed"   },
  { key:"cancelled",  label:"Cancelled"   },
] as const;

type Props = { navigation: NativeStackNavigationProp<never> };

export function JobsListScreen({ navigation }: Props) {
  const [activeTab, setActiveTab] = useState("");

  const jobs = useApi(
    useCallback(() => jobsApi.myJobs({ limit:"30", ...(activeTab ? { status:activeTab } : {}) }), [activeTab])
  );

  const fmt = (d:string) => new Date(d).toLocaleDateString("en-IN",{ day:"numeric", month:"short" });

  function renderJob({ item:j }: { item:Job }) {
    return (
      <TouchableOpacity style={s.jobCard} activeOpacity={0.85}
        onPress={() => navigation.navigate("JobDetail" as never, { jobId:j.id } as never)}>
        <View style={s.jobTop}>
          <View style={{ flex:1 }}>
            <Text style={s.jobNum}>{j.job_number}</Text>
            <Text style={s.service}>{j.service_type} · {j.city}</Text>
          </View>
          <JobStatusBadge status={j.status} size="sm" />
        </View>
        <Text style={s.customer}>{j.customer_name ?? "—"}</Text>
        {j.customer_address && (
          <Text style={s.address} numberOfLines={1}>📍 {j.customer_address}</Text>
        )}
        {j.sla_minutes != null && j.minutes_in_status != null
          && ["in_progress","arrived","en_route","quality_check"].includes(j.status) && (
          <View style={{ marginTop:8 }}>
            <SlaTimer slaMinutes={j.sla_minutes} minutesInStatus={j.minutes_in_status} />
          </View>
        )}
        <View style={s.jobBottom}>
          <Text style={s.date}>{fmt(j.created_at)}</Text>
          {j.job_value != null && (
            <Text style={s.value}>₹{j.job_value.toLocaleString("en-IN")}</Text>
          )}
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
          data={jobs.data?.jobs ?? []}
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
