import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { fieldOpsJobsApi } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { jobId:string };
type Props  = NativeStackScreenProps<{ JobTracking:Params }, "JobTracking">;

/**
 * UX-06 ROUND 2: rewired to the real, confirmed field_ops.Job customer surface
 * (GET /v1/customer/jobs/{id}, GET /v1/customer/jobs/{id}/progress — see
 * app/engines/field_ops/customer_router.py + service.py). The prior scaffold's
 * live staff-geo-location polling (jobsApi.trackStaff -> /v1/geo/staff/{id}/location)
 * had no confirmed real customer-facing contract this round, so it was removed
 * rather than left calling a guessed endpoint — the job progress-steps timeline
 * (a real, confirmed contract) is shown instead. Re-add live location tracking
 * once a real customer-facing geo endpoint is confirmed.
 *
 * UX-07 Pass 3b: migrated off the static `theme`/`gs` import onto useTheme().
 */
export function JobTrackingScreen({ route }: Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const { jobId } = route.params;
  const job      = useApi(useCallback(() => fieldOpsJobsApi.get(jobId), [jobId]));
  const progress = useApi(useCallback(() => fieldOpsJobsApi.progress(jobId), [jobId]));

  const j = job.data;
  const p = progress.data;

  const STEPS = [
    { statuses:["pending_assignment"],       label:"Finding technician", icon:"🔍" },
    { statuses:["assigned","accepted"],      label:"Technician confirmed",icon:"✅" },
    { statuses:["en_route"],                 label:"On the way",          icon:"🚗" },
    { statuses:["arrived"],                  label:"Arrived at location", icon:"📍" },
    { statuses:["in_progress","parts_required","parts_sourced","resumed","quality_check"],
                                             label:"Work in progress",    icon:"🔧" },
    { statuses:["completed","closed"],       label:"Completed",           icon:"🎉" },
  ];

  function stepState(statuses:string[]) {
    if (!p) return "pending";
    if (statuses.includes(p.status)) return "active";
    const allStatuses = STEPS.flatMap(s=>s.statuses);
    const curIdx  = allStatuses.indexOf(p.status);
    const stepIdx = allStatuses.indexOf(statuses[0]);
    return curIdx > stepIdx ? "done" : "pending";
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      {job.loading ? <Skeleton height={90}/> : j && (
        <Card style={{ gap:8 }}>
          <View style={[s.row,{justifyContent:"space-between"}]}>
            <Text style={s.jobNum}>{j.job_number}</Text>
            <JobStatusBadge status={j.status}/>
          </View>
          {j.title && <Text style={s.serviceType}>{j.title}</Text>}
          {p?.assigned_staff && (
            <Text style={s.staffName}>👨‍🔧 {p.assigned_staff.name}</Text>
          )}
        </Card>
      )}

      <Card>
        <Text style={[s.label,{marginBottom:14}]}>Job Progress</Text>
        {STEPS.map((step, i) => {
          const state = stepState(step.statuses);
          return (
            <View key={i} style={[s.row,{gap:14,paddingBottom:i<STEPS.length-1?14:0,alignItems:"flex-start"}]}>
              <View style={{alignItems:"center",width:28}}>
                <View style={[s.stepDot,
                  state==="done"  && s.stepDotDone,
                  state==="active"&& s.stepDotActive]}>
                  <Text style={{fontSize:12}}>{state==="done"?"✓":step.icon}</Text>
                </View>
                {i<STEPS.length-1 && <View style={[s.stepLine,state==="done"&&s.stepLineDone]}/>}
              </View>
              <View style={{flex:1,paddingTop:4}}>
                <Text style={[s.stepLabel,
                  state==="active"&&{color:theme.colors.brand,fontWeight:"700"},
                  state==="pending"&&{color:theme.colors.textTertiary}]}>
                  {step.label}
                </Text>
              </View>
            </View>
          );
        })}
      </Card>
    </ScrollView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:     { flex:1, backgroundColor:theme.colors.bg },
    row:        { flexDirection:"row", alignItems:"center" },
    label:      { fontSize:theme.font.size.xs, fontWeight:theme.font.weight.bold,
                  color:theme.colors.textTertiary, textTransform:"uppercase", letterSpacing:1 },
    content:    { padding:16, gap:14 },
    jobNum:     { fontSize:theme.font.size.md, fontWeight:"700", color:theme.colors.textPrimary },
    serviceType:{ fontSize:theme.font.size.base, color:theme.colors.textSecondary },
    staffName:  { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
    stepDot:    { width:28, height:28, borderRadius:14, backgroundColor:theme.colors.surfaceSunken,
                  alignItems:"center", justifyContent:"center" },
    stepDotDone:{ backgroundColor:theme.colors.brand },
    stepDotActive:{ backgroundColor:theme.colors.brand, opacity:0.7 },
    stepLine:   { width:2, flex:1, backgroundColor:theme.colors.border, marginTop:4, minHeight:14 },
    stepLineDone:{ backgroundColor:theme.colors.brand },
    stepLabel:  { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
  });
}
