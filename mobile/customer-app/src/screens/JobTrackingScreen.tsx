import React, { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { jobsApi, type StaffLocation } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { CUSTOMER_STATUS_LABEL } from "../lib/jobStatus";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { jobId:string };
type Props  = NativeStackScreenProps<{ JobTracking:Params }, "JobTracking">;

export function JobTrackingScreen({ route }: Props) {
  const { jobId } = route.params;
  const [staffLoc, setStaffLoc]   = useState<StaffLocation | null>(null);
  const [locError, setLocError]   = useState<string | null>(null);

  const job = useApi(useCallback(() => jobsApi.get(jobId), [jobId]));

  // Poll job status every 30s and fetch staff location
  useEffect(() => {
    async function pollLocation() {
      const j = await jobsApi.get(jobId);
      if (j.assigned_staff_id) {
        try {
          const loc = await jobsApi.trackStaff(j.assigned_staff_id);
          setStaffLoc(loc);
        } catch { setLocError("Location unavailable"); }
      }
    }
    pollLocation();
    const interval = setInterval(pollLocation, 30_000);
    return () => clearInterval(interval);
  }, [jobId]);

  const j = job.data;
  const fmtTime = (d:string) => new Date(d).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"});

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
    if (!j) return "pending";
    if (statuses.includes(j.status)) return "active";
    const allStatuses = STEPS.flatMap(s=>s.statuses);
    const curIdx  = allStatuses.indexOf(j.status);
    const stepIdx = allStatuses.indexOf(statuses[0]);
    return curIdx > stepIdx ? "done" : "pending";
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {/* Status bar */}
      {job.loading ? <Skeleton height={90}/> : j && (
        <Card style={{ gap:8 }}>
          <View style={[gs.row,{justifyContent:"space-between"}]}>
            <Text style={s.jobNum}>{j.job_number}</Text>
            <JobStatusBadge status={j.status}/>
          </View>
          <Text style={s.serviceType}>{j.service_type}</Text>
          {j.assigned_staff && (
            <Text style={s.staffName}>👨‍🔧 {j.assigned_staff}</Text>
          )}
        </Card>
      )}

      {/* Map placeholder / location info */}
      <Card style={{ minHeight:180, alignItems:"center", justifyContent:"center", gap:12 }}>
        {locError ? (
          <>
            <Text style={{ fontSize:32 }}>📍</Text>
            <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary, textAlign:"center" }}>
              {locError}
            </Text>
            <Text style={{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" }}>
              Map tracking will appear once the technician is en route
            </Text>
          </>
        ) : staffLoc ? (
          <>
            <Text style={{ fontSize:40 }}>🗺️</Text>
            <Text style={{ fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary }}>
              Technician Location
            </Text>
            <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary }}>
              Last updated: {fmtTime(staffLoc.last_seen_at)}
            </Text>
            {staffLoc.accuracy_m && (
              <Text style={{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary }}>
                Accuracy: ±{Math.round(staffLoc.accuracy_m)}m
              </Text>
            )}
          </>
        ) : (
          <>
            <Text style={{ fontSize:32 }}>🔍</Text>
            <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary }}>
              Waiting for location…
            </Text>
          </>
        )}
      </Card>

      {/* Progress steps */}
      <Card>
        <Text style={[gs.label,{marginBottom:14}]}>Job Progress</Text>
        {STEPS.map((step, i) => {
          const state = stepState(step.statuses);
          return (
            <View key={i} style={[gs.row,{gap:14,paddingBottom:i<STEPS.length-1?14:0,alignItems:"flex-start"}]}>
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
                {state==="active"&&j&&(
                  <Text style={{fontSize:theme.font.size.xs,color:theme.colors.accent,marginTop:2}}>
                    Current status: {CUSTOMER_STATUS_LABEL[j.status]??j.status}
                  </Text>
                )}
              </View>
            </View>
          );
        })}
      </Card>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:       { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  jobNum:        { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  serviceType:   { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  staffName:     { fontSize:theme.font.size.base, color:theme.colors.textSecondary },
  stepDot:       { width:28, height:28, borderRadius:14, backgroundColor:theme.colors.border,
                   alignItems:"center", justifyContent:"center" },
  stepDotActive: { backgroundColor:theme.colors.accentLight, borderWidth:2, borderColor:theme.colors.brand },
  stepDotDone:   { backgroundColor:theme.colors.successBg },
  stepLine:      { width:2, flex:1, backgroundColor:theme.colors.border, marginTop:4, minHeight:16 },
  stepLineDone:  { backgroundColor:theme.colors.success },
  stepLabel:     { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
});
