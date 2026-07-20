import React, { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { staffApi, type WorkingHours } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatCard } from "../components/StatCard";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Skeleton } from "../components/Skeleton";
import { AvailabilityControl } from "../components/ux05/AvailabilityControl";
import { deriveRole } from "../lib/ux05/permissions";
import { theme, gs } from "../styles/theme";
import type { AvailabilityView } from "../types/ux05";

const DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"] as const;
const DAY_LABEL: Record<string,string> = { monday:"Mon", tuesday:"Tue", wednesday:"Wed",
  thursday:"Thu", friday:"Fri", saturday:"Sat", sunday:"Sun" };

export function ProfileScreen() {
  const { user, logout } = useAuth();
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [localHours, setLocalHours] = useState<WorkingHours>({});

  const staff       = useApi(useCallback(() => staffApi.get(),         []));
  const performance = useApi(useCallback(() => staffApi.performance(), []));

  const [saving, setSaving] = useState(false);

  const s2 = staff.data;
  const p  = performance.data;
  const role = user ? deriveRole(user) : "technician";
  const [workStatus, setWorkStatus] = useState<AvailabilityView["workStatus"]>("available");

  function openSchedule() {
    const wh = s2?.working_hours ?? {};
    const init: WorkingHours = {};
    DAYS.forEach(d => { init[d] = wh[d] ?? { start:"09:00", end:"18:00", is_working:d!=="sunday" }; });
    setLocalHours(init);
    setEditingSchedule(true);
  }

  async function saveSchedule() {
    setSaving(true);
    try {
      await staffApi.updateSchedule(localHours);
      staff.refetch();
      setEditingSchedule(false);
    } catch (e:unknown) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed to save.");
    } finally { setSaving(false); }
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {/* Profile header */}
      <View style={s.header}>
        <View style={s.avatar}>
          <Text style={s.avatarText}>{user?.full_name?.[0] ?? "S"}</Text>
        </View>
        <View style={{ flex:1 }}>
          <Text style={s.name}>{user?.full_name ?? "Staff"}</Text>
          <Text style={s.phone}>{staff.data?.phone ?? "—"}</Text>
          {/* Canonical role only -- staff|technician, from the same
              fail-closed deriveRole() used everywhere else. Designation is
              descriptive display text derived from specialisations, never
              used for any authorization decision. */}
          <Text style={s.roleTag}>{role === "staff" ? "Staff" : "Technician"}</Text>
        </View>
      </View>

      {/* Assigned services (real -- from StaffUser.specialisations) */}
      <Card style={{ gap:8 }}>
        <Text style={gs.label}>Assigned Services</Text>
        <Text style={s.skills}>{staff.data?.specialisations?.join(" · ") || "—"}</Text>
        <Text style={[gs.label, { marginTop:8 }]}>Assigned Areas · Certifications · Supported Brands</Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live endpoint carries area/certification/supported-brand data on StaffUser today.</Text>
      </Card>

      {/* Availability (workstream 21) */}
      <AvailabilityControl
        availability={{
          meta:{readiness:"mock_design_only"}, workStatus,
          accountStatus: s2?.status ?? "unknown", currentJobStatus: null,
        }}
        onChange={setWorkStatus}
      />

      {/* Recent activity -- MOCK_DESIGN_ONLY, no live activity-feed endpoint */}
      <Card style={{ gap:6 }}>
        <Text style={gs.label}>Recent Activity</Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live per-staff activity-feed endpoint exists yet.</Text>
      </Card>

      {/* Performance stats */}
      {performance.loading ? <Skeleton height={80} />
      : p && (
        <View style={s.statsRow}>
          <StatCard label="Score" value={`${p.composite_score.toFixed(0)}/100`} accent={theme.colors.accent} />
          <StatCard label="Rating" value={`★ ${p.avg_customer_rating.toFixed(1)}`} accent={theme.colors.warning} />
          <StatCard label="Jobs"   value={String(p.jobs_completed)}                                            />
          <StatCard label="On-time" value={`${p.sla_adherence_rate.toFixed(0)}%`} accent={theme.colors.success} />
        </View>
      )}

      {/* Performance signal bars */}
      {p && (
        <Card>
          <Text style={[gs.label, { marginBottom:12 }]}>Performance Breakdown</Text>
          {Object.entries(p.signal_values).map(([key, val]) => {
            const pct  = Math.min(100, Math.max(0, Number(val)));
            const barC = pct>=75?theme.colors.success:pct>=50?theme.colors.warning:theme.colors.danger;
            return (
              <View key={key} style={{ marginBottom:12 }}>
                <View style={[gs.row, { justifyContent:"space-between", marginBottom:5 }]}>
                  <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textTransform:"capitalize" }}>
                    {key.replace(/_/g," ")}
                  </Text>
                  <Text style={{ fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary }}>
                    {pct.toFixed(0)}
                  </Text>
                </View>
                <View style={{ height:6, backgroundColor:theme.colors.border, borderRadius:3, overflow:"hidden" }}>
                  <View style={{ height:"100%", width:`${pct}%`, backgroundColor:barC, borderRadius:3 }} />
                </View>
              </View>
            );
          })}
        </Card>
      )}

      {/* Schedule */}
      <Card>
        <View style={[gs.row, { justifyContent:"space-between", marginBottom:14 }]}>
          <Text style={gs.label}>Weekly Schedule</Text>
          <TouchableOpacity onPress={openSchedule}>
            <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.accent, fontWeight:"600" }}>
              Edit
            </Text>
          </TouchableOpacity>
        </View>
        {staff.loading ? <Skeleton height={160} />
        : DAYS.map(d => {
          const dh = s2?.working_hours?.[d] ?? { start:"09:00", end:"18:00", is_working:d!=="sunday" };
          return (
            <View key={d} style={[gs.row, { justifyContent:"space-between", paddingVertical:7,
              borderBottomWidth:1, borderBottomColor:theme.colors.border }]}>
              <Text style={{ fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary, width:40 }}>
                {DAY_LABEL[d]}
              </Text>
              <Text style={{ fontSize:theme.font.size.sm, color:dh.is_working ? theme.colors.textSecondary : theme.colors.textTertiary, flex:1 }}>
                {dh.is_working ? `${dh.start} – ${dh.end}` : "Day off"}
              </Text>
              <View style={[s.statusDot, { backgroundColor:dh.is_working ? theme.colors.success : theme.colors.border }]} />
            </View>
          );
        })}
      </Card>

      {/* Edit schedule */}
      {editingSchedule && (
        <Card>
          <Text style={[gs.label, { marginBottom:14 }]}>Edit Schedule</Text>
          {DAYS.map(d => {
            const dh = localHours[d] ?? { start:"09:00", end:"18:00", is_working:true };
            return (
              <View key={d} style={[gs.row, { gap:10, paddingVertical:8,
                borderBottomWidth:1, borderBottomColor:theme.colors.border }]}>
                <Switch value={dh.is_working}
                  onValueChange={v => setLocalHours(prev => ({ ...prev, [d]:{ ...dh, is_working:v } }))}
                  trackColor={{ true:theme.colors.accent }} />
                <Text style={{ fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary, width:36 }}>
                  {DAY_LABEL[d]}
                </Text>
                {dh.is_working && (
                  <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary }}>
                    {dh.start} – {dh.end}
                  </Text>
                )}
              </View>
            );
          })}
          <View style={{ flexDirection:"row", gap:10, marginTop:16 }}>
            <Button label="Cancel" variant="ghost" size="sm" onPress={() => setEditingSchedule(false)} style={{ flex:1 }} />
            <Button label="Save" variant="primary" size="sm" loading={saving} onPress={saveSchedule} style={{ flex:1 }} />
          </View>
        </Card>
      )}

      {/* Logout */}
      <Button label="Sign Out" variant="danger" size="lg" onPress={() => {
        Alert.alert("Sign Out", "Are you sure?", [
          { text:"Cancel", style:"cancel" },
          { text:"Sign Out", style:"destructive", onPress: logout },
        ]);
      }} fullWidth />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:   { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  header:    { flexDirection:"row", alignItems:"center", gap:14, backgroundColor:theme.colors.surface,
               borderRadius:theme.radius.lg, padding:theme.spacing.base, ...theme.shadow.sm },
  avatar:    { width:58, height:58, borderRadius:29, backgroundColor:theme.colors.brand,
               alignItems:"center", justifyContent:"center" },
  avatarText:{ fontSize:theme.font.size.xxl, fontWeight:"800", color:"#fff" },
  name:      { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  phone:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  skills:    { fontSize:theme.font.size.xs, color:theme.colors.accent, marginTop:4 },
  statsRow:  { flexDirection:"row", gap:10 },
  statusDot: { width:8, height:8, borderRadius:4 },
  roleTag:   { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.accent, marginTop:4, textTransform:"uppercase" },
  mockNote:  { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
