import React, { useCallback, useMemo } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi } from "../lib/api";
import { StatCard } from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

// MODULE-L5-36: the MODULE-L5-33 fix rewired this to
// GET /v1/jobs/staff/{staff_id}/earnings -- a REAL endpoint, but one that
// counts field_ops' `Job` model, which is dead scaffolding with 0 rows
// platform-wide (see MODULE-L5-36). It would always report zero for every
// real job a technician actually does. There is no job-value/price field
// anywhere reachable by staff on the real ServiceJob pipeline (deliberately
// -- the safe booking view excludes pricing from staff visibility), so
// "earnings" in the money sense isn't something this screen can show
// honestly yet. Rewired to derive real completed-job counts from the same
// live /v1/staff/service-jobs list the Jobs tab uses, and dropped the
// fabricated job-value/rating stats rather than show fake zeros.
export function EarningsScreen() {
  const jobs = useApi(useCallback(() => jobsApi.myJobs(), []));

  const stats = useMemo(() => {
    const all = jobs.data?.jobs ?? [];
    const completed = all.filter(j => j.status === "completed");
    const monthStart = new Date(); monthStart.setDate(1); monthStart.setHours(0,0,0,0);
    const thisMonth = completed.filter(j => new Date(j.created_at) >= monthStart);
    return { total: completed.length, thisMonth: thisMonth.length };
  }, [jobs.data]);

  return (
    <ScrollView style={gs.screen} contentContainerStyle={{ paddingBottom:32 }}>
      <View style={s.summaryWrap}>
        {jobs.loading ? (
          <Skeleton height={120} />
        ) : (
          <>
            <View style={s.totalBox}>
              <Text style={s.totalLabel}>Jobs Completed (Lifetime)</Text>
              <Text style={s.totalValue}>{String(stats.total)}</Text>
            </View>
            <View style={s.statsRow}>
              <StatCard label="This Month" value={String(stats.thisMonth)} accent={theme.colors.success} />
              <StatCard label="Assigned" value={String((jobs.data?.jobs ?? []).length)} />
            </View>
          </>
        )}
      </View>

      <View style={{ paddingHorizontal:theme.spacing.base, paddingTop:16 }}>
        <Text style={[s.note, { color:theme.colors.textTertiary }]}>
          Payout, commission, and job value are handled by your employer, not this app.
        </Text>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  summaryWrap:{ backgroundColor:theme.colors.brand, padding:theme.spacing.base, gap:16, paddingBottom:20 },
  totalBox:   { gap:6 },
  totalLabel: { fontSize:theme.font.size.sm, color:"rgba(255,255,255,0.65)", fontWeight:"600", textTransform:"uppercase", letterSpacing:0.6 },
  totalValue: { fontSize:theme.font.size.huge, fontWeight:"800", color:"#fff" },
  statsRow:   { flexDirection:"row", gap:10 },
  note:       { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
});
