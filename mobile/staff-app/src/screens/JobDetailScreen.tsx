import React, { useCallback, useMemo, useState } from "react";
import { Alert, KeyboardAvoidingView, Modal, Platform, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { jobsApi } from "../lib/api";
import { NEXT_ACTION, ACTION_LABEL, ACTION_VARIANT, STATUS_LABEL, type JobAction } from "../lib/transitions";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { PipelineBadge } from "../components/ux05/PipelineBadge";
import { CustomerContactCard } from "../components/ux05/CustomerContactCard";
import { AddressCard } from "../components/ux05/AddressCard";
import { theme, gs } from "../styles/theme";
import { useAppTheme } from "../context/ThemeContext";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { CustomerContactView } from "../types/ux05";

type Params = { jobId:string };
type Props  = NativeStackScreenProps<{ JobDetail:Params }, "JobDetail">;

// MODULE-L5-36: rewired from field_ops (0 rows platform-wide) to the real
// service_jobs pipeline (home_service_assignment for accept/reject,
// execution for the on-the-way -> ... -> complete lifecycle). Detail is now
// {job, assignment, booking} -- ServiceJob itself carries no customer name/
// phone/price; those live on the booking (safe view: name/city/issue only,
// no phone or price exposed to staff) or aren't tracked at all. "Close Job"
// + "Record Payment" collapse into the single validated `complete` action
// (work_summary + collected_amount).
const ACTION_FN: Record<JobAction, (jobId:string, arg?:string) => Promise<unknown>> = {
  accept:              (id) => jobsApi.accept(id),
  reject:              (id, reason) => jobsApi.reject(id, reason ?? ""),
  onTheWay:            (id) => jobsApi.onTheWay(id),
  reachedSite:         (id) => jobsApi.reachedSite(id),
  startInspection:     (id) => jobsApi.startInspection(id),
  completeInspection:  (id) => jobsApi.completeInspection(id),
  startService:        (id) => jobsApi.startService(id),
  workDone:            (id) => jobsApi.workDone(id),
  complete:            () => Promise.reject(new Error("complete requires work_summary/collected_amount")),
};

export function JobDetailScreen({ route }: Props) {
  const { jobId } = route.params;
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  const [rejectModal, setRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [completeModal, setCompleteModal] = useState(false);
  const [workSummary, setWorkSummary] = useState("");
  const [collectedAmount, setCollectedAmount] = useState("");

  const detail = useApi(useCallback(() => jobsApi.get(jobId), [jobId]));

  const actionState = useAction(useCallback(async (action:JobAction, arg?:string) => {
    if (action === "reject") return jobsApi.reject(jobId, arg ?? "");
    return ACTION_FN[action](jobId, arg);
  }, [jobId]));

  const completeAction = useAction(useCallback(
    (summary:string, amount:number) => jobsApi.complete(jobId, summary, amount), [jobId]
  ));

  const j = detail.data?.job;
  const assignment = detail.data?.assignment;
  const booking = detail.data?.booking;
  const actions = j ? (NEXT_ACTION[j.status] ?? []) : [];

  const fmtDate = (d:string) => new Date(d).toLocaleString("en-IN",{ day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" });

  async function handleAction(action:JobAction) {
    if (action === "reject") { setRejectModal(true); return; }
    if (action === "complete") { setCompleteModal(true); return; }
    const res = await actionState.execute(action);
    if (res) detail.refetch();
  }

  async function handleReject() {
    if (!rejectReason.trim()) { Alert.alert("Required", "Please enter a reason."); return; }
    const res = await actionState.execute("reject", rejectReason.trim());
    if (res) { setRejectModal(false); setRejectReason(""); detail.refetch(); }
  }

  async function handleComplete() {
    const amount = parseFloat(collectedAmount);
    if (!workSummary.trim()) { Alert.alert("Required", "Please enter a work summary."); return; }
    if (!amount && amount !== 0) { Alert.alert("Required", "Please enter the amount collected."); return; }
    const res = await completeAction.execute(workSummary.trim(), amount);
    if (res) {
      setCompleteModal(false); setWorkSummary(""); setCollectedAmount("");
      detail.refetch();
      Alert.alert("Job completed.", "Work summary and collected amount recorded.");
    }
  }

  if (detail.loading) return (
    <ScrollView style={[gs.screen, { backgroundColor:colors.bg }]} contentContainerStyle={{ padding:theme.spacing.base, gap:14 }}>
      {[...Array(4)].map((_,i) => <Skeleton key={i} height={80} />)}
    </ScrollView>
  );

  return (
    <ScrollView style={[gs.screen, { backgroundColor:colors.bg }]} contentContainerStyle={s.content}>
      {j && (
        <>
          {/* Header */}
          <Card>
            <View style={[gs.row, { justifyContent:"space-between", marginBottom:8 }]}>
              <Text style={s.jobNum}>{j.job_number}</Text>
              <JobStatusBadge status={j.status} />
            </View>
            <PipelineBadge provenance={{ pipeline:"service_booking_service_job", sourceBookingId:j.booking_id, jobId:j.id, jobModel:"ServiceJob" }} />
            {j.city && <Text style={s.city}>{j.city}{j.zipcode ? `, ${j.zipcode}` : ""}</Text>}
            {j.scheduled_date && (
              <Text style={s.city}>🗓 {j.scheduled_date}{j.scheduled_time_window ? ` · ${j.scheduled_time_window}` : ""}</Text>
            )}
          </Card>

          {/* Customer contact + address (workstream 11) -- built from the
              same safe booking view already fetched, no new call */}
          {booking && (() => {
            const contact: CustomerContactView = {
              meta: { readiness: "production_ready" },
              name: booking.customer_name, city: booking.city, zipcode: booking.zipcode,
              issueSummary: booking.issue_summary, preferredDate: booking.preferred_date,
              preferredTimeWindow: booking.preferred_time_window,
              callSupported: false, messageSupported: false,
            };
            return (
              <>
                <CustomerContactCard contact={contact} />
                <AddressCard contact={contact} />
              </>
            );
          })()}

          {/* Booking info (safe view -- no phone/price exposed to staff) */}
          {booking && (
            <Card style={{ gap:8 }}>
              <Text style={gs.label}>Booking</Text>
              <Text style={s.custName}>{booking.customer_name ?? "—"}</Text>
              {booking.issue_summary && <Text style={s.notes}>{booking.issue_summary}</Text>}
              <Text style={s.booking}>#{booking.booking_number}</Text>
            </Card>
          )}

          {assignment?.rejection_reason && (
            <Card>
              <Text style={gs.label}>Rejection Reason</Text>
              <Text style={s.notes}>{assignment.rejection_reason}</Text>
            </Card>
          )}

          {j.completion_data && (
            <Card style={{ gap:6 }}>
              <Text style={gs.label}>Completion</Text>
              <Text style={s.notes}>{String(j.completion_data.work_summary ?? "")}</Text>
              <Text style={s.custName}>₹{Number(j.completion_data.collected_amount ?? 0).toLocaleString("en-IN")} collected</Text>
            </Card>
          )}

          {/* Actions */}
          {actions.length > 0 && (
            <Card>
              <Text style={[gs.label, { marginBottom:12 }]}>Actions</Text>
              <View style={s.actionGrid}>
                {actions.map(a => (
                  <Button key={a}
                    label={ACTION_LABEL[a]}
                    variant={ACTION_VARIANT[a]}
                    size="md"
                    loading={actionState.loading}
                    onPress={() => handleAction(a)}
                    style={{ flex:1, minWidth:140 }}
                  />
                ))}
              </View>
              {actionState.error && <Text style={s.errText}>{actionState.error}</Text>}
            </Card>
          )}
        </>
      )}

      {!j && !detail.loading && (
        <Card><Text style={s.notes}>Job not found or not assigned to you.</Text></Card>
      )}

      {/* Reject Modal */}
      <Modal visible={rejectModal} transparent animationType="slide" onRequestClose={() => setRejectModal(false)}>
        <KeyboardAvoidingView style={s.modalOverlay} behavior={Platform.OS==="ios"?"padding":"height"}>
          <View style={s.modalSheet}>
            <Text style={s.modalTitle}>Reject this job</Text>
            <Text style={s.modalSub}>A reason is required.</Text>
            <TextInput style={s.textarea} value={rejectReason} onChangeText={setRejectReason}
              placeholder="Why are you rejecting this job?" placeholderTextColor={colors.textTertiary}
              multiline numberOfLines={3} textAlignVertical="top" />
            {actionState.error && <Text style={s.errText}>{actionState.error}</Text>}
            <View style={{ gap:10 }}>
              <Button label="Submit Rejection" variant="danger" size="lg"
                loading={actionState.loading} onPress={handleReject} fullWidth />
              <Button label="Cancel" variant="ghost" size="md"
                onPress={() => setRejectModal(false)} fullWidth />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Complete Modal */}
      <Modal visible={completeModal} transparent animationType="slide" onRequestClose={() => setCompleteModal(false)}>
        <KeyboardAvoidingView style={s.modalOverlay} behavior={Platform.OS==="ios"?"padding":"height"}>
          <View style={s.modalSheet}>
            <Text style={s.modalTitle}>Complete Job</Text>
            <Text style={s.modalSub}>Work summary and amount collected are both required.</Text>
            <TextInput style={s.textarea} value={workSummary} onChangeText={setWorkSummary}
              placeholder="e.g. AC unit cleaned, filter replaced. Customer satisfied."
              placeholderTextColor={colors.textTertiary}
              multiline numberOfLines={4} textAlignVertical="top" />
            <TextInput style={s.input} value={collectedAmount} onChangeText={setCollectedAmount}
              placeholder="Amount Collected (₹) *" keyboardType="numeric"
              placeholderTextColor={colors.textTertiary} />
            <Text style={s.modalSub}>Payment mode: Customer Pays Provider Directly</Text>
            {completeAction.error && <Text style={s.errText}>{completeAction.error}</Text>}
            <View style={{ gap:10 }}>
              <Button label="Submit & Complete" variant="success" size="lg"
                loading={completeAction.loading} onPress={handleComplete} fullWidth />
              <Button label="Cancel" variant="ghost" size="md"
                onPress={() => setCompleteModal(false)} fullWidth />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </ScrollView>
  );
}

// UX-05B FIX 2 (item 2): converted to reactive theme colors, same
// useMemo(makeStyles(colors)) pattern used by ScheduleScreen/HomeScreen/etc.
// Deliberately deferred in Round 7 because this screen holds the real
// money-collection ("Complete Job") modal and needed dedicated regression
// coverage before touching it -- see
// src/screens/__tests__/JobDetailScreen.test.tsx for that coverage, added
// alongside this conversion (not after).
function makeStyles(colors: ReturnType<typeof import("../styles/theme").getColors>) {
  return StyleSheet.create({
    content:    { padding:theme.spacing.base, gap:12, paddingBottom:32 },
    jobNum:     { fontSize:theme.font.size.base, fontWeight:"700", color:colors.textPrimary },
    city:       { fontSize:theme.font.size.sm, color:colors.textSecondary, marginTop:2 },
    custName:   { fontSize:theme.font.size.lg, fontWeight:"600", color:colors.textPrimary },
    booking:    { fontSize:theme.font.size.xs, color:colors.textTertiary },
    actionGrid: { flexDirection:"row", flexWrap:"wrap", gap:10 },
    errText:    { fontSize:theme.font.size.sm, color:colors.dangerText, marginTop:8 },
    notes:      { fontSize:theme.font.size.base, color:colors.textSecondary, lineHeight:22 },
    input:        { borderWidth:1, borderColor:colors.border, borderRadius:theme.radius.lg,
                    padding:12, fontSize:theme.font.size.base, color:colors.textPrimary,
                    backgroundColor:colors.surfaceSunken },
    modalOverlay:{ flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.45)" },
    modalSheet:  { backgroundColor:colors.surface, borderTopLeftRadius:24, borderTopRightRadius:24,
                   padding:24, gap:14, paddingBottom:40 },
    modalTitle:  { fontSize:theme.font.size.xl, fontWeight:"700", color:colors.textPrimary },
    modalSub:    { fontSize:theme.font.size.sm, color:colors.textSecondary },
    textarea:    { borderWidth:1, borderColor:colors.border, borderRadius:theme.radius.lg,
                   padding:12, fontSize:theme.font.size.base, color:colors.textPrimary,
                   minHeight:100, backgroundColor:colors.surfaceSunken },
  });
}
