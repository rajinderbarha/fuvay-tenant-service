import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { PartsRequestStatusView } from "../../types/ux05";

const STATE_LABEL: Record<string,string> = {
  requested:"Requested", under_review:"Under Review", approved:"Approved",
  rejected:"Rejected", installed:"Installed",
};
const STATE_COLOR: Record<string,{bg:string;text:string}> = {
  requested:{bg:theme.colors.infoBg,text:theme.colors.infoText},
  under_review:{bg:theme.colors.warningBg,text:theme.colors.warningText},
  approved:{bg:theme.colors.successBg,text:theme.colors.successText},
  rejected:{bg:theme.colors.dangerBg,text:theme.colors.dangerText},
  installed:{bg:theme.colors.successBg,text:theme.colors.successText},
};

/**
 * Technician-facing read-only parts-request status. Deliberately renders
 * NO approve/reject/mark-installed affordance -- technicianActions on the
 * view model is typed to only ever contain "add_note" (see types/ux05.ts).
 */
export function PartsRequestStatusCard({ item }: { item:PartsRequestStatusView }) {
  const c = STATE_COLOR[item.state];
  return (
    <View style={[gs.card, s.card]} testID="parts-request-status-card"
      accessibilityRole="summary"
      accessibilityLabel={`${item.partName}, quantity ${item.quantity}, status ${STATE_LABEL[item.state]}`}>
      <View style={s.row}>
        <Text style={s.name}>{item.partName} × {item.quantity}</Text>
        <View style={[s.badge, { backgroundColor:c.bg }]}>
          <Text style={[s.badgeText, { color:c.text }]}>{STATE_LABEL[item.state]}</Text>
        </View>
      </View>
      <Text style={s.meta}>Requested {item.requestedAt}</Text>
      {item.providerResponse && <Text style={s.response}>Provider: {item.providerResponse}</Text>}
    </View>
  );
}

const s = StyleSheet.create({
  card:     { gap:6 },
  row:      { flexDirection:"row", justifyContent:"space-between", alignItems:"center" },
  name:     { fontSize:theme.font.size.md, fontWeight:"700", color:theme.colors.textPrimary },
  badge:    { borderRadius:999, paddingHorizontal:8, paddingVertical:2 },
  badgeText:{ fontSize:theme.font.size.xs, fontWeight:"700" },
  meta:     { fontSize:theme.font.size.sm, color:theme.colors.textTertiary },
  response: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
});
