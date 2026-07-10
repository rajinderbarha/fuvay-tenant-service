import React, { useCallback } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { earningsApi, type CommissionRecord } from "../lib/api";
import { StatCard } from "../components/StatCard";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

export function EarningsScreen() {
  const summary     = useApi(useCallback(() => earningsApi.summary(),      []));
  const commissions = useApi(useCallback(() => earningsApi.commissions(30), []));

  const fmt     = (n:number) => `₹${n.toLocaleString("en-IN")}`;
  const fmtDate = (d:string) => new Date(d).toLocaleDateString("en-IN",{ day:"numeric", month:"short" });

  function renderRecord({ item:r }: { item:CommissionRecord }) {
    return (
      <View style={s.row}>
        <View style={{ flex:1 }}>
          <Text style={s.jobNum}>{r.job_number ?? r.job_id.slice(0,8)}</Text>
          <Text style={s.date}>Deducted {fmtDate(r.deducted_at)} · Rate: {(r.rate*100).toFixed(0)}%</Text>
        </View>
        <View style={{ alignItems:"flex-end" }}>
          <Text style={s.amount}>-{fmt(r.amount)}</Text>
          <Text style={s.jobVal}>of {fmt(r.job_value)}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={gs.screen}>
      {/* Summary */}
      <View style={s.summaryWrap}>
        {summary.loading ? (
          <Skeleton height={120} />
        ) : (
          <>
            <View style={s.totalBox}>
              <Text style={s.totalLabel}>Total Earned (Lifetime)</Text>
              <Text style={s.totalValue}>{summary.data ? fmt(summary.data.total_earned) : "—"}</Text>
            </View>
            <View style={s.statsRow}>
              <StatCard label="This Month" value={summary.data ? fmt(summary.data.this_month) : "—"}
                accent={theme.colors.success} />
              <StatCard label="Pending" value={summary.data ? fmt(summary.data.pending_payout) : "—"}
                accent={theme.colors.warning} />
              <StatCard label="Jobs Done" value={String(summary.data?.jobs_completed ?? "—")} />
            </View>
          </>
        )}
      </View>

      {/* Commission records */}
      <Text style={[gs.label, { paddingHorizontal:theme.spacing.base, marginTop:4 }]}>Commission Deductions</Text>
      {commissions.loading ? (
        <View style={{ padding:theme.spacing.base, gap:10 }}>
          {[...Array(5)].map((_,i) => <Skeleton key={i} height={56} />)}
        </View>
      ) : (
        <FlatList
          data={commissions.data?.records ?? []}
          renderItem={renderRecord}
          keyExtractor={r => r.id}
          onRefresh={() => { summary.refetch(); commissions.refetch(); }}
          refreshing={commissions.loading}
          contentContainerStyle={{ paddingBottom:32 }}
          ItemSeparatorComponent={() => <View style={gs.sep} />}
          ListEmptyComponent={
            <View style={{ alignItems:"center", paddingTop:48, gap:10 }}>
              <Text style={{ fontSize:40 }}>💰</Text>
              <Text style={{ color:theme.colors.textTertiary }}>No commissions recorded yet</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  summaryWrap:{ backgroundColor:theme.colors.brand, padding:theme.spacing.base, gap:16, paddingBottom:20 },
  totalBox:   { gap:6 },
  totalLabel: { fontSize:theme.font.size.sm, color:"rgba(255,255,255,0.65)", fontWeight:"600", textTransform:"uppercase", letterSpacing:0.6 },
  totalValue: { fontSize:theme.font.size.huge, fontWeight:"800", color:"#fff" },
  statsRow:   { flexDirection:"row", gap:10 },
  row:        { flexDirection:"row", alignItems:"center", padding:14, backgroundColor:theme.colors.surface, gap:10 },
  jobNum:     { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  date:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:3 },
  amount:     { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.dangerText },
  jobVal:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
