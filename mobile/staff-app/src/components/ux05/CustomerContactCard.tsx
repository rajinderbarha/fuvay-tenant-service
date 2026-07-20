import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { CustomerContactView } from "../../types/ux05";

/**
 * Minimal-necessary-data customer contact card. No phone number is
 * rendered -- neither Job nor the safe BookingSummary view expose one to
 * staff (see types/ux05.ts CustomerContactView comment); "Call" is
 * therefore not offered as a real action (callSupported is always false
 * until a contact-relay endpoint exists). "Message" opens the real staff
 * chat thread (chatApi) instead.
 */
export function CustomerContactCard({ contact, onMessage }: { contact:CustomerContactView; onMessage?:() => void }) {
  return (
    <View style={[gs.card, s.card]} testID="customer-contact-card">
      <Text style={gs.label}>Customer</Text>
      <Text style={s.name}>{contact.name ?? "—"}</Text>
      {contact.issueSummary && <Text style={s.issue}>{contact.issueSummary}</Text>}
      <View style={s.actions}>
        {contact.callSupported ? (
          <TouchableOpacity style={s.actionBtn} accessibilityRole="button" accessibilityLabel="Call customer">
            <Text style={s.actionText}>📞 Call</Text>
          </TouchableOpacity>
        ) : (
          <View style={[s.actionBtn, s.disabled]} accessibilityRole="text" accessibilityLabel="Call unavailable for this job">
            <Text style={s.disabledText}>📞 Call unavailable</Text>
          </View>
        )}
        {contact.messageSupported && (
          <TouchableOpacity style={s.actionBtn} onPress={onMessage} accessibilityRole="button" accessibilityLabel="Message customer">
            <Text style={s.actionText}>💬 Message</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card:        { gap:8 },
  name:        { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
  issue:       { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  actions:     { flexDirection:"row", gap:10, marginTop:6 },
  // UX-05 Round 4 a11y pass: 40pt -> 44pt to meet the minimum touch-target size.
  actionBtn:   { flex:1, height:44, borderRadius:theme.radius.md, borderWidth:1, borderColor:theme.colors.border,
                 alignItems:"center", justifyContent:"center" },
  actionText:  { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
  disabled:    { backgroundColor:theme.colors.surfaceSunken },
  disabledText:{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
