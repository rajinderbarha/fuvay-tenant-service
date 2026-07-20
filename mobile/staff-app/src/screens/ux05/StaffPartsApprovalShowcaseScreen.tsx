import React, { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";
import { useAuth } from "../../context/AuthContext";
import { deriveRole, permissionsFor, hasPermission } from "../../lib/ux05/permissions";
import type { PartsRequestStatusView } from "../../types/ux05";

const QUEUE: PartsRequestStatusView[] = [
  { meta:{readiness:"mock_design_only"}, id:"pr_1", jobId:"sj_9f21ac", partName:"AC Compressor Capacitor",
    quantity:1, requestedAt:"2026-07-18 10:20", note:"Original capacitor swollen/burst.",
    providerResponse:null, state:"under_review", technicianActions:["add_note"] },
];

/**
 * DEV-ONLY, staff-only. Never reachable by a technician role (deriveRole()
 * fails closed to technician for every current real user, so this screen
 * will show the restricted state for everyone until a real staff role +
 * parts_request:approve grant exist). Approve/reject/mark-installed are
 * NEVER exposed to a technician-derived role, matching the hard constraint.
 */
export function StaffPartsApprovalShowcaseScreen() {
  const { user } = useAuth();
  const role = user ? deriveRole(user) : "technician";
  const permissions = permissionsFor(role, user?.tenant_id ?? null);
  const canApprove = hasPermission(permissions, "parts_request:approve");
  const [queue, setQueue] = useState(QUEUE);

  if (role !== "staff" || !canApprove) {
    return (
      <ScrollView style={gs.screen} contentContainerStyle={s.content}>
        <PermissionRestrictedState reason={
          role !== "staff"
            ? "This account is presented as technician (fail-closed default) -- Parts Approval is staff-only."
            : "parts_request:approve is not granted (MOCK_DESIGN_ONLY -- no live StaffPermission endpoint yet)."
        } />
      </ScrollView>
    );
  }

  function decide(id: string, decision: "approved" | "rejected") {
    setQueue(prev => prev.map(p => p.id === id ? { ...p, state: decision } : p));
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="staff-parts-approval-showcase">
      {queue.map(item => (
        <View key={item.id} style={[gs.card, { gap:8 }]}>
          <Text style={s.name}>{item.partName} × {item.quantity}</Text>
          <Text style={s.note}>{item.note}</Text>
          <Text style={s.state}>Current: {item.state}</Text>
          {item.state === "under_review" && (
            <View style={{ flexDirection:"row", gap:10 }}>
              <Button label="Approve" variant="success" onPress={() => decide(item.id, "approved")} style={{ flex:1 }} />
              <Button label="Reject" variant="danger" onPress={() => decide(item.id, "rejected")} style={{ flex:1 }} />
            </View>
          )}
        </View>
      ))}
      <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live parts-approval endpoint exists yet; decisions here are local-state only.</Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  name:    { fontSize:theme.font.size.md, fontWeight:"700", color:theme.colors.textPrimary },
  note:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  state:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  mockNote:{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
});
