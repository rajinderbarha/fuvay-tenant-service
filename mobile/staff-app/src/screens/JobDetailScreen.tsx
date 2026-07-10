import React, { useCallback, useState } from "react";
import { Alert, KeyboardAvoidingView, Modal, Platform, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View, Linking } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { useLocation } from "../hooks/useLocation";
import { jobsApi } from "../lib/api";
import { VALID_TRANSITIONS, STATUS_LABEL } from "../lib/transitions";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { SlaTimer } from "../components/SlaTimer";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { jobId:string };
type Props  = NativeStackScreenProps<{ JobDetail:Params }, "JobDetail">;

const TRANSITION_VARIANT: Record<string, "primary"|"success"|"danger"|"secondary"> = {
  accepted:"primary", en_route:"primary", arrived:"primary", in_progress:"primary",
  quality_check:"secondary", completed:"success", cancelled:"danger",
  parts_required:"secondary", parts_sourced:"secondary", resumed:"secondary",
};

export function JobDetailScreen({ route, navigation }: Props) {
  const { jobId } = route.params;
  const [closeModal,  setCloseModal]  = useState(false);
  const [closingNote, setClosingNote] = useState("");
  const [paymentModal,   setPaymentModal]   = useState(false);
  const [amountInput,    setAmountInput]    = useState("");
  const [paymentMode,    setPaymentMode]    = useState("cash");
  const [paymentNote,    setPaymentNote]    = useState("");

  const job     = useApi(useCallback(() => jobsApi.get(jobId),     [jobId]));
  const history = useApi(useCallback(() => jobsApi.history(jobId), [jobId]));
  const { startTracking, stopTracking } = useLocation();

  const updateAction = useAction(useCallback(
    (status:string, notes?:string) => jobsApi.updateStatus(jobId, status, notes), [jobId]
  ));
  const closeAction = useAction(useCallback(
    (notes:string) => jobsApi.close(jobId, notes), [jobId]
  ));
  const paymentAction = useAction(useCallback(
    (amount:number, mode:string, notes?:string) => jobsApi.recordPayment(jobId, amount, mode, notes), [jobId]
  ));

  const j         = job.data;
  const allowed   = j ? (VALID_TRANSITIONS[j.status] ?? []) : [];
  const fmtDate   = (d:string) => new Date(d).toLocaleString("en-IN",{ day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" });

  async function handleTransition(next:string) {
    if (next === "en_route") await startTracking();
    if (["completed","closed","cancelled"].includes(next)) stopTracking();
    const res = await updateAction.execute(next);
    if (res) { job.refetch(); history.refetch(); }
  }

  async function handleClose() {
    if (!closingNote.trim()) { Alert.alert("Required", "Please enter closing notes."); return; }
    const res = await closeAction.execute(closingNote.trim());
    if (res) {
      setCloseModal(false); setClosingNote(""); job.refetch();
      Alert.alert("Job completed successfully.",
        "Provider usage credit deduction will be applied to tenant account.");
    }
  }

  async function handleRecordPayment() {
    const amount = parseFloat(amountInput);
    if (!amount || amount <= 0) { Alert.alert("Required", "Please enter the amount collected."); return; }
    const res = await paymentAction.execute(amount, paymentMode, paymentNote.trim() || undefined);
    if (res) { setPaymentModal(false); setAmountInput(""); setPaymentNote(""); job.refetch(); }
  }

  if (job.loading) return (
    <ScrollView style={gs.screen} contentContainerStyle={{ padding:theme.spacing.base, gap:14 }}>
      {[...Array(4)].map((_,i) => <Skeleton key={i} height={80} />)}
    </ScrollView>
  );

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {j && (
        <>
          {/* Header */}
          <Card>
            <View style={[gs.row, { justifyContent:"space-between", marginBottom:8 }]}>
              <Text style={s.jobNum}>{j.job_number}</Text>
              <JobStatusBadge status={j.status} />
            </View>
            <Text style={s.serviceType}>{j.service_type}</Text>
            <Text style={s.city}>{j.city}</Text>
            {j.sla_minutes != null && j.minutes_in_status != null && (
              <View style={{ marginTop:10 }}>
                <SlaTimer slaMinutes={j.sla_minutes} minutesInStatus={j.minutes_in_status} />
              </View>
            )}
          </Card>

          {/* Customer info */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>Customer</Text>
            <Text style={s.custName}>{j.customer_name ?? "—"}</Text>
            {j.customer_phone && (
              <TouchableOpacity style={s.callBtn}
                onPress={() => Linking.openURL(`tel:${j.customer_phone}`)}>
                <Text style={s.callBtnText}>📱 Call {j.customer_phone}</Text>
              </TouchableOpacity>
            )}
            {j.customer_address && (
              <TouchableOpacity style={s.mapBtn}
                onPress={() => Linking.openURL(`maps://maps.google.com/maps?q=${encodeURIComponent(j.customer_address!)}`)}>
                <Text style={s.mapBtnText}>📍 Open in Maps</Text>
              </TouchableOpacity>
            )}
          </Card>

          {/* Payment Collection — customer pays provider directly; ServiceOS never
              collects the service payment for Home Services. */}
          {j.quoted_price != null && (
            <Card style={{ gap:8 }}>
              <Text style={gs.label}>Payment Collection</Text>
              <View style={s.paymentRow}>
                <Text style={s.paymentLabel}>Service Price</Text>
                <Text style={s.paymentValue}>₹{j.quoted_price.toLocaleString("en-IN")}</Text>
              </View>
              <View style={s.paymentRow}>
                <Text style={s.paymentLabel}>ServiceOS Credit Applied</Text>
                <Text style={s.paymentValue}>₹{(j.customer_credit_applied ?? 0).toLocaleString("en-IN")}</Text>
              </View>
              <View style={s.paymentRow}>
                <Text style={[s.paymentLabel, { fontWeight:"700" }]}>Collect From Customer</Text>
                <Text style={[s.paymentValue, { fontWeight:"700", color:theme.colors.accent }]}>
                  ₹{(j.payable_to_provider ?? j.quoted_price).toLocaleString("en-IN")}
                </Text>
              </View>
              <Text style={s.paymentNote}>Collection Mode: Direct payment to provider</Text>
              <Text style={s.paymentNote}>Platform Payment: Not collected by ServiceOS</Text>
              {j.payment_recorded ? (
                <Text style={[s.paymentNote, { color:theme.colors.successText, fontWeight:"600" }]}>
                  ✓ Payment recorded — ₹{(j.amount_collected ?? 0).toLocaleString("en-IN")} collected
                </Text>
              ) : (
                <Button label="Record Payment Collected" variant="primary" size="md"
                  onPress={() => { setAmountInput(String(j.payable_to_provider ?? j.quoted_price ?? "")); setPaymentModal(true); }}
                  style={{ marginTop:6 }} />
              )}
            </Card>
          )}

          {/* Status transitions */}
          {allowed.length > 0 && (
            <Card>
              <Text style={[gs.label, { marginBottom:12 }]}>Update Status</Text>
              <View style={s.transGrid}>
                {allowed.map(next => (
                  <Button key={next}
                    label={`→ ${STATUS_LABEL[next] ?? next}`}
                    variant={TRANSITION_VARIANT[next] ?? "secondary"}
                    size="md"
                    loading={updateAction.loading}
                    onPress={() => handleTransition(next)}
                    style={{ flex:1, minWidth:140 }}
                  />
                ))}
              </View>
              {updateAction.error && (
                <Text style={s.errText}>{updateAction.error}</Text>
              )}
            </Card>
          )}

          {/* Close job — requires payment recorded first when a payable amount is owed. */}
          {j.status === "completed" && (
            j.quoted_price != null && (j.payable_to_provider ?? j.quoted_price) > 0 && !j.payment_recorded ? (
              <Text style={s.errText}>Record the payment collected before closing this job.</Text>
            ) : (
              <Button label="Close Job & Submit" variant="primary" size="lg"
                onPress={() => setCloseModal(true)} fullWidth />
            )
          )}

          {/* Notes */}
          {j.notes && (
            <Card>
              <Text style={gs.label}>Job Notes</Text>
              <Text style={s.notes}>{j.notes}</Text>
            </Card>
          )}

          {/* Timeline */}
          <Card>
            <Text style={[gs.label, { marginBottom:12 }]}>History</Text>
            {history.loading ? <Skeleton height={80} />
            : (history.data?.history ?? []).map((h, i, arr) => (
              <View key={i} style={[gs.row, { gap:12, paddingBottom:i<arr.length-1?14:0, alignItems:"flex-start" }]}>
                <View style={{ alignItems:"center", width:20 }}>
                  <View style={[s.dot, i===0 && s.dotActive]} />
                  {i < arr.length-1 && <View style={s.line} />}
                </View>
                <View style={{ flex:1 }}>
                  <Text style={s.histStatus}>{STATUS_LABEL[h.status] ?? h.status}</Text>
                  <Text style={s.histDate}>{fmtDate(h.changed_at)}</Text>
                  {h.notes && <Text style={s.histNotes}>{h.notes}</Text>}
                </View>
              </View>
            ))}
          </Card>
        </>
      )}

      {/* Record Payment Modal */}
      <Modal visible={paymentModal} transparent animationType="slide" onRequestClose={() => setPaymentModal(false)}>
        <KeyboardAvoidingView style={s.modalOverlay} behavior={Platform.OS==="ios"?"padding":"height"}>
          <View style={s.modalSheet}>
            <Text style={s.modalTitle}>Record Payment</Text>
            <Text style={s.modalSub}>
              Amount collected must match payable-to-provider amount ₹{(j?.payable_to_provider ?? j?.quoted_price ?? 0).toLocaleString("en-IN")}.
            </Text>
            <TextInput style={s.input} value={amountInput} onChangeText={setAmountInput}
              placeholder="Amount Collected *" keyboardType="numeric"
              placeholderTextColor={theme.colors.textTertiary} />
            <View style={s.transGrid}>
              {["cash","upi","card"].map(m => (
                <Button key={m} label={m.toUpperCase()} size="sm"
                  variant={paymentMode===m ? "primary" : "secondary"}
                  onPress={() => setPaymentMode(m)} style={{ flex:1 }} />
              ))}
            </View>
            <TextInput style={s.textarea} value={paymentNote} onChangeText={setPaymentNote}
              placeholder="Note (optional)" placeholderTextColor={theme.colors.textTertiary}
              multiline numberOfLines={2} textAlignVertical="top" />
            {paymentAction.error && <Text style={s.errText}>{paymentAction.error}</Text>}
            <View style={{ gap:10 }}>
              <Button label="Confirm Payment Collected" variant="success" size="lg"
                loading={paymentAction.loading} onPress={handleRecordPayment} fullWidth />
              <Button label="Cancel" variant="ghost" size="md"
                onPress={() => setPaymentModal(false)} fullWidth />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Close Job Modal */}
      <Modal visible={closeModal} transparent animationType="slide" onRequestClose={() => setCloseModal(false)}>
        <KeyboardAvoidingView style={s.modalOverlay} behavior={Platform.OS==="ios"?"padding":"height"}>
          <View style={s.modalSheet}>
            <Text style={s.modalTitle}>Close Job</Text>
            <Text style={s.modalSub}>Add closing notes before submitting. Required.</Text>
            <TextInput style={s.textarea} value={closingNote} onChangeText={setClosingNote}
              placeholder="e.g. AC unit cleaned, filter replaced. Customer satisfied."
              placeholderTextColor={theme.colors.textTertiary}
              multiline numberOfLines={4} textAlignVertical="top" />
            {closeAction.error && <Text style={s.errText}>{closeAction.error}</Text>}
            <View style={{ gap:10 }}>
              <Button label="Submit & Close" variant="success" size="lg"
                loading={closeAction.loading} onPress={handleClose} fullWidth />
              <Button label="Cancel" variant="ghost" size="md"
                onPress={() => setCloseModal(false)} fullWidth />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:    { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  jobNum:     { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  serviceType:{ fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary, marginBottom:3 },
  city:       { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  custName:   { fontSize:theme.font.size.lg, fontWeight:"600", color:theme.colors.textPrimary },
  callBtn:    { backgroundColor:theme.colors.successBg, borderRadius:theme.radius.md, padding:12, borderWidth:1, borderColor:theme.colors.successBorder },
  callBtnText:{ color:theme.colors.successText, fontWeight:"600", fontSize:theme.font.size.base, textAlign:"center" },
  mapBtn:     { backgroundColor:theme.colors.infoBg, borderRadius:theme.radius.md, padding:12, borderWidth:1, borderColor:theme.colors.infoBorder },
  mapBtnText: { color:theme.colors.infoText, fontWeight:"600", fontSize:theme.font.size.base, textAlign:"center" },
  transGrid:  { flexDirection:"row", flexWrap:"wrap", gap:10 },
  paymentRow:   { flexDirection:"row", justifyContent:"space-between" },
  paymentLabel: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  paymentValue: { fontSize:theme.font.size.sm, color:theme.colors.textPrimary, fontWeight:"600" },
  paymentNote:  { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  input:        { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                  padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                  backgroundColor:theme.colors.surfaceSunken },
  errText:    { fontSize:theme.font.size.sm, color:theme.colors.dangerText, marginTop:8 },
  notes:      { fontSize:theme.font.size.base, color:theme.colors.textSecondary, lineHeight:22 },
  dot:        { width:12, height:12, borderRadius:6, backgroundColor:theme.colors.border, marginTop:3 },
  dotActive:  { backgroundColor:theme.colors.accent },
  line:       { width:2, flex:1, backgroundColor:theme.colors.border, marginTop:4, minHeight:24 },
  histStatus: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  histDate:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  histNotes:  { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:3 },
  modalOverlay:{ flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.45)" },
  modalSheet:  { backgroundColor:theme.colors.surface, borderTopLeftRadius:24, borderTopRightRadius:24,
                 padding:24, gap:14, paddingBottom:40 },
  modalTitle:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  modalSub:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  textarea:    { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                 padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                 minHeight:100, backgroundColor:theme.colors.surfaceSunken },
});
