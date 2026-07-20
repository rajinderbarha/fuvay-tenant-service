import React, { useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { PartsRequestStatusCard } from "../../components/ux05/PartsRequestStatusCard";
import type { PartsRequestDraftView, PartsRequestStatusView } from "../../types/ux05";

/**
 * DEV-ONLY showcase -- not reachable from production navigation.
 * API_CONTRACT_REQUIRED: src/lib/api.ts has no partsApi export today (no
 * parts-request endpoint is wired into the real staff-app backend contract
 * yet). This renders the intended technician create+track UI shape against
 * local component state only, so the interaction pattern can be reviewed
 * before a real endpoint exists. Never claims a submission succeeded
 * against a real backend -- the "Submit Request" button appends to local
 * state and is clearly a design fixture, not a live call.
 *
 * Enforces: ServiceJob-only, technician never approves/rejects/marks-
 * installed (technicianActions is always ["add_note"]).
 */
const FIXTURE_JOB_ID = "sj_9f21ac";

const INITIAL: PartsRequestStatusView[] = [
  { meta:{readiness:"mock_design_only"}, id:"pr_1", jobId:FIXTURE_JOB_ID, partName:"AC Compressor Capacitor", quantity:1,
    requestedAt:"2026-07-18 10:20", note:"Original capacitor swollen/burst.", providerResponse:null,
    state:"under_review", technicianActions:["add_note"] },
  { meta:{readiness:"mock_design_only"}, id:"pr_2", jobId:FIXTURE_JOB_ID, partName:"Copper Refrigerant Line (2m)", quantity:1,
    requestedAt:"2026-07-16 09:05", note:null, providerResponse:"Approved -- available at branch store.",
    state:"approved", technicianActions:["add_note"] },
];

export function PartsRequestShowcaseScreen() {
  const [items, setItems] = useState(INITIAL);
  const [draft, setDraft] = useState<Partial<PartsRequestDraftView>>({
    jobId: FIXTURE_JOB_ID, partName:"", description:"", quantity:1, reason:"", note:"",
  });

  function submit() {
    if (!draft.partName?.trim() || !draft.reason?.trim()) return;
    setItems(prev => [{
      meta:{readiness:"mock_design_only"}, id:`pr_${Date.now()}`, jobId:FIXTURE_JOB_ID,
      partName:draft.partName!.trim(), quantity:draft.quantity ?? 1,
      requestedAt:new Date().toISOString().slice(0,16).replace("T"," "),
      note:draft.reason!.trim(), providerResponse:null, state:"requested", technicianActions:["add_note"],
    }, ...prev]);
    setDraft({ jobId: FIXTURE_JOB_ID, partName:"", description:"", quantity:1, reason:"", note:"" });
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="parts-request-showcase">
      <Card style={{ gap:10 }}>
        <Text style={gs.label}>New Parts Request (ServiceJob {FIXTURE_JOB_ID})</Text>
        <TextInput style={s.input} placeholder="Part name *" value={draft.partName}
          onChangeText={v => setDraft(d => ({ ...d, partName:v }))} placeholderTextColor={theme.colors.textTertiary} />
        <TextInput style={s.input} placeholder="Quantity" keyboardType="numeric"
          value={String(draft.quantity ?? 1)} onChangeText={v => setDraft(d => ({ ...d, quantity:Number(v)||1 }))}
          placeholderTextColor={theme.colors.textTertiary} />
        <TextInput style={s.textarea} placeholder="Reason *" multiline
          value={draft.reason} onChangeText={v => setDraft(d => ({ ...d, reason:v }))}
          placeholderTextColor={theme.colors.textTertiary} />
        <Button label="Submit Request (design fixture)" variant="primary" onPress={submit} fullWidth />
        <Text style={s.note}>MOCK_DESIGN_ONLY -- no live parts-request endpoint wired yet.</Text>
      </Card>

      <Text style={[gs.label, { marginTop:8 }]}>My Parts Requests</Text>
      {items.map(item => <PartsRequestStatusCard key={item.id} item={item} />)}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  input:   { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
             padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
             backgroundColor:theme.colors.surfaceSunken },
  textarea:{ borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
             padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
             minHeight:70, backgroundColor:theme.colors.surfaceSunken },
  note:    { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
