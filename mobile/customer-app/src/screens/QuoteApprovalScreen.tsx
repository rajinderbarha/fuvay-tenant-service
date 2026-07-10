import React, { useCallback, useState } from "react";
import {
  Alert, Modal, ScrollView, StyleSheet,
  Text, TextInput, TouchableOpacity, View, ActivityIndicator,
} from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { quoteApi } from "../lib/api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { jobId:string; bookingNumber?:string };
type Props  = NativeStackScreenProps<{ QuoteApproval:Params }, "QuoteApproval">;

export function QuoteApprovalScreen({ route, navigation }: Props) {
  const { jobId, bookingNumber } = route.params;
  const [rejectModal, setRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [decided, setDecided] = useState<"approved"|"rejected"|null>(null);

  const quote = useApi(useCallback(() => quoteApi.get(jobId), [jobId]));

  const approveAction = useAction(useCallback(() => quoteApi.approve(jobId), [jobId]));
  const rejectAction  = useAction(useCallback(
    (reason:string) => quoteApi.reject(jobId, reason), [jobId]
  ));

  const q = quote.data;
  const fmtPrice = (n:number) => `₹${n.toLocaleString("en-IN")}`;
  const fmtDate  = (d:string) => new Date(d).toLocaleDateString("en-IN",{ day:"numeric", month:"short", year:"numeric" });

  async function handleApprove() {
    Alert.alert(
      "Approve Repair?",
      `The technician will proceed with the repair for ${q ? fmtPrice(q.quoted_price) : "the quoted amount"}. This amount will be charged on completion.`,
      [
        { text:"Cancel", style:"cancel" },
        {
          text:"Yes, Approve",
          onPress: async () => {
            const res = await approveAction.execute();
            if (res) setDecided("approved");
          }
        },
      ]
    );
  }

  async function handleReject() {
    if (!rejectReason.trim()) {
      Alert.alert("Reason Required", "Please tell us why you are declining."); return;
    }
    const res = await rejectAction.execute(rejectReason.trim());
    if (res) { setRejectModal(false); setDecided("rejected"); }
  }

  // ── Success states ──────────────────────────────────────────────────────
  if (decided === "approved") {
    return (
      <View style={[gs.screen, { alignItems:"center", justifyContent:"center", padding:32, gap:16 }]}>
        <Text style={{ fontSize:64 }}>✅</Text>
        <Text style={{ fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.textPrimary, textAlign:"center" }}>
          Repair Approved!
        </Text>
        <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary, textAlign:"center", lineHeight:24 }}>
          The technician has been notified and will proceed with the repair.
        </Text>
        <Card style={{ width:"100%", gap:6 }}>
          {q && (
            <>
              <View style={[gs.row, { justifyContent:"space-between" }]}>
                <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary }}>Total to pay on completion</Text>
                <Text style={{ fontSize:theme.font.size.xl, fontWeight:"800", color:theme.colors.brand }}>
                  {fmtPrice(q.quoted_price)}
                </Text>
              </View>
              <View style={[gs.row, { justifyContent:"space-between" }]}>
                <Text style={{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary }}>Visit fee already paid</Text>
                <Text style={{ fontSize:theme.font.size.base, color:theme.colors.success }}>
                  - {fmtPrice(q.visit_fee)}
                </Text>
              </View>
              <View style={[{ height:1, backgroundColor:theme.colors.border, marginVertical:4 }]}/>
              <View style={[gs.row, { justifyContent:"space-between" }]}>
                <Text style={{ fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary }}>Balance due</Text>
                <Text style={{ fontSize:theme.font.size.xl, fontWeight:"800", color:theme.colors.textPrimary }}>
                  {fmtPrice(q.quoted_price - q.visit_fee)}
                </Text>
              </View>
            </>
          )}
        </Card>
        <Button label="Track Job" variant="primary" size="lg" fullWidth
          onPress={() => navigation.navigate("JobTracking" as never, { jobId } as never)} />
        <Button label="Go Home" variant="ghost" size="md" fullWidth
          onPress={() => navigation.navigate("Home" as never)} />
      </View>
    );
  }

  if (decided === "rejected") {
    return (
      <View style={[gs.screen, { alignItems:"center", justifyContent:"center", padding:32, gap:16 }]}>
        <Text style={{ fontSize:64 }}>👍</Text>
        <Text style={{ fontSize:theme.font.size.xxl, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" }}>
          Understood
        </Text>
        <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary, textAlign:"center", lineHeight:24 }}>
          The repair has been declined. The visit fee has been charged. The technician has been informed.
        </Text>
        <Button label="Go Home" variant="primary" size="lg" fullWidth
          onPress={() => navigation.navigate("Home" as never)} />
      </View>
    );
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerTitle}>Repair Quote</Text>
        {bookingNumber && <Text style={s.headerSub}>{bookingNumber}</Text>}
        <View style={s.pendingBadge}>
          <Text style={s.pendingText}>⏳ Awaiting your approval</Text>
        </View>
      </View>

      {quote.loading ? (
        <View style={{ gap:14 }}>
          {[...Array(3)].map((_,i) => <Skeleton key={i} height={90} />)}
        </View>
      ) : q ? (
        <>
          {/* Findings */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>What the Technician Found</Text>
            <Text style={s.findings}>{q.findings}</Text>
          </Card>

          {/* Recommended work */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>Recommended Work</Text>
            <Text style={s.findings}>{q.recommended_work}</Text>
            {q.technician_notes && (
              <Text style={s.techNote}>💬 "{q.technician_notes}"</Text>
            )}
          </Card>

          {/* Price breakdown */}
          <Card style={{ gap:10 }}>
            <Text style={gs.label}>Price Breakdown</Text>
            {[
              { label:"Labour",         amount:q.labour_cost },
              { label:"Parts & Material",amount:q.parts_cost },
              { label:"Visit Fee (already paid)", amount:q.visit_fee, credit:true },
            ].map(row => (
              <View key={row.label} style={[gs.row, { justifyContent:"space-between", paddingVertical:6,
                borderBottomWidth:1, borderBottomColor:theme.colors.border }]}>
                <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary }}>{row.label}</Text>
                <Text style={{ fontSize:theme.font.size.base, fontWeight:"600",
                  color: row.credit ? theme.colors.success : theme.colors.textPrimary }}>
                  {row.credit ? "-" : "+"} {fmtPrice(row.amount)}
                </Text>
              </View>
            ))}
            <View style={[gs.row, { justifyContent:"space-between", paddingTop:6 }]}>
              <Text style={{ fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary }}>
                Total
              </Text>
              <Text style={{ fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.brand }}>
                {fmtPrice(q.quoted_price)}
              </Text>
            </View>
            <Text style={{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary }}>
              Balance due on completion: {fmtPrice(q.quoted_price - q.visit_fee)}
            </Text>
          </Card>

          {/* Quote expiry */}
          <View style={s.expiryBox}>
            <Text style={s.expiryText}>
              ⏰ This quote expires on <Text style={{ fontWeight:"700" }}>{fmtDate(q.expires_at)}</Text>
            </Text>
          </View>

          {/* Action buttons */}
          {(approveAction.error || rejectAction.error) && (
            <View style={s.errBox}>
              <Text style={s.errText}>{approveAction.error || rejectAction.error}</Text>
            </View>
          )}

          <View style={{ gap:10 }}>
            <Button label={`✓ Approve — ${fmtPrice(q.quoted_price)}`}
              variant="success" size="lg" fullWidth
              loading={approveAction.loading}
              onPress={handleApprove} />
            <Button label="✕ Decline Repair"
              variant="danger" size="md" fullWidth
              onPress={() => setRejectModal(true)} />
          </View>

          <View style={s.helpBox}>
            <Text style={s.helpText}>
              Questions? You can chat with the technician in the Chat tab before deciding.
            </Text>
          </View>
        </>
      ) : (
        <View style={{ alignItems:"center", paddingTop:60, gap:10 }}>
          <Text style={{ fontSize:36 }}>📋</Text>
          <Text style={{ color:theme.colors.textTertiary }}>Quote not available yet</Text>
        </View>
      )}

      {/* Reject modal */}
      <Modal visible={rejectModal} transparent animationType="slide"
        onRequestClose={() => setRejectModal(false)}>
        <View style={s.overlay}>
          <View style={s.sheet}>
            <Text style={s.sheetTitle}>Decline Repair</Text>
            <Text style={s.sheetSub}>
              Please tell us why. This helps us improve. The visit fee has already been charged.
            </Text>
            <TextInput style={s.textarea} value={rejectReason} onChangeText={setRejectReason}
              placeholder="e.g. Cost is too high, will manage myself…"
              placeholderTextColor={theme.colors.textTertiary}
              multiline numberOfLines={4} textAlignVertical="top" />
            {rejectAction.error && (
              <Text style={s.errText}>{rejectAction.error}</Text>
            )}
            <View style={{ gap:10 }}>
              <Button label="Confirm Decline" variant="danger" size="lg" fullWidth
                loading={rejectAction.loading} onPress={handleReject} />
              <Button label="Go Back" variant="ghost" size="md" fullWidth
                onPress={() => setRejectModal(false)} />
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:     { padding:theme.spacing.base, gap:14, paddingBottom:40 },
  header:      { gap:6 },
  headerTitle: { fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.textPrimary },
  headerSub:   { fontSize:theme.font.size.sm, color:theme.colors.textTertiary },
  pendingBadge:{ backgroundColor:theme.colors.warningBg, borderRadius:99, paddingHorizontal:12,
                 paddingVertical:5, alignSelf:"flex-start", borderWidth:1, borderColor:theme.colors.warningBorder },
  pendingText: { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.warningText },
  findings:    { fontSize:theme.font.size.base, color:theme.colors.textPrimary, lineHeight:24 },
  techNote:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, fontStyle:"italic",
                 padding:10, backgroundColor:theme.colors.surfaceSunken, borderRadius:theme.radius.md },
  expiryBox:   { backgroundColor:theme.colors.infoBg, borderRadius:theme.radius.md, padding:10,
                 borderWidth:1, borderColor:theme.colors.infoBorder },
  expiryText:  { fontSize:theme.font.size.sm, color:theme.colors.infoText },
  helpBox:     { alignItems:"center", padding:12 },
  helpText:    { fontSize:theme.font.size.sm, color:theme.colors.textTertiary, textAlign:"center", lineHeight:20 },
  errBox:      { backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md,
                 padding:12, borderWidth:1, borderColor:theme.colors.dangerBorder },
  errText:     { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
  overlay:     { flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.45)" },
  sheet:       { backgroundColor:theme.colors.surface, borderTopLeftRadius:28, borderTopRightRadius:28,
                 padding:24, gap:14, paddingBottom:40 },
  sheetTitle:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  sheetSub:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  textarea:    { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                 padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                 minHeight:100, backgroundColor:theme.colors.surfaceSunken },
});
