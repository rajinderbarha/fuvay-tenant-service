import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { earningsApi } from "../lib/api";
import { StatCard } from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

// MODULE-L5-33: rewired to the one real backend endpoint
// (GET /v1/jobs/staff/{staff_id}/earnings) -- a completed-jobs-value
// summary, not a payout ledger. ServiceOS charges the tenant commission per
// job, not the technician, so there is no "total earned / pending payout /
// commission deductions" concept to show; this screen no longer pretends
// there is one.
export function EarningsScreen() {
  const summary = useApi(useCallback(() => earningsApi.summary(), []));

  const fmt = (n:number) => `₹${n.toLocaleString("en-IN")}`;

  return (
    <ScrollView style={gs.screen} contentContainerStyle={{ paddingBottom:32 }}>
      <View style={s.summaryWrap}>
        {summary.loading ? (
          <Skeleton height={120} />
        ) : (
          <>
            <View style={s.totalBox}>
              <Text style={s.totalLabel}>Job Value Handled (Lifetime)</Text>
              <Text style={s.totalValue}>{summary.data ? fmt(summary.data.job_value_total) : "—"}</Text>
            </View>
            <View style={s.statsRow}>
              <StatCard label="This Month" value={summary.data ? fmt(summary.data.job_value_this_month) : "—"}
                accent={theme.colors.success} />
              <StatCard label="Jobs Done" value={String(summary.data?.jobs_completed_total ?? "—")} />
              <StatCard label="Avg Rating"
                value={summary.data?.average_rating != null ? summary.data.average_rating.toFixed(1) : "—"}
                accent={theme.colors.warning} />
            </View>
          </>
        )}
      </View>

      <Text style={[gs.label, { paddingHorizontal:theme.spacing.base, marginTop:16 }]}>This Month</Text>
      <View style={{ paddingHorizontal:theme.spacing.base, paddingTop:8 }}>
        <Text style={s.note}>
          {summary.data
            ? `${summary.data.jobs_completed_this_month} job${summary.data.jobs_completed_this_month === 1 ? "" : "s"} completed this month.`
            : "—"}
        </Text>
        <Text style={[s.note, { marginTop:8, color:theme.colors.textTertiary }]}>
          Payout and commission are handled by your employer, not this app.
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
