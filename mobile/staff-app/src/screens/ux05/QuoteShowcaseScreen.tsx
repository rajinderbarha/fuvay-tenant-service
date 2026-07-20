import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { QuoteSummaryView } from "../../types/ux05";

/**
 * Quote presentation (workstream 17). Checked src/lib/api.ts in full for
 * anything quote-related before building this -- there is no quoteApi, no
 * quote field on Job/JobDetail/ExecutionEvent, nothing. This is entirely
 * API_CONTRACT_REQUIRED. Renders a read-only view-only presentation of a
 * fixture QuoteSummaryView; technicianCanEdit/staffCanReview are shown as
 * disabled labels, not interactive controls, since there is no real
 * submit/approve path to wire them to. NEVER renders an "Approve" or
 * "Finalize Price" action for a technician (that authority stays with the
 * customer/platform per the hard constraint, and isn't in this view model
 * at all).
 */
const FIXTURE: QuoteSummaryView = {
  meta: { readiness: "mock_design_only" }, jobId: "sj_9f21ac", status: "draft",
  lineItemsSummary: "AC Compressor Capacitor (1) — est. ₹850; Labor — est. ₹500",
  technicianCanEdit: true, staffCanReview: false,
};

const STATUS_LABEL: Record<QuoteSummaryView["status"], string> = {
  draft: "Draft", submitted_for_review: "Submitted for Review",
  sent_to_customer: "Sent to Customer", approved: "Approved by Customer", rejected: "Rejected by Customer",
};

export function QuoteShowcaseScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="quote-showcase">
      <View style={[gs.card, { gap:10 }]}>
        <Text style={gs.label}>Quote — {FIXTURE.jobId}</Text>
        <Text style={s.status}>{STATUS_LABEL[FIXTURE.status]}</Text>
        <Text style={s.body}>{FIXTURE.lineItemsSummary}</Text>
        <View style={s.capRow}>
          <Text style={s.cap}>Technician can edit line items: {FIXTURE.technicianCanEdit ? "Yes (draft only)" : "No"}</Text>
          <Text style={s.cap}>Staff can review/approve: {FIXTURE.staffCanReview ? "Yes (with permission)" : "Not applicable to this account"}</Text>
        </View>
        <Text style={s.note}>
          Technicians never finalize price, approve on the customer's behalf, or override platform pricing
          boundaries -- those actions don't exist in this view model at all.
        </Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live quote endpoint exists anywhere in lib/api.ts today.</Text>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:  { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  status:   { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.accent },
  body:     { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
  capRow:   { gap:4, marginTop:6 },
  cap:      { fontSize:theme.font.size.xs, color:theme.colors.textSecondary },
  note:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:6 },
  mockNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, fontWeight:"700" },
});
