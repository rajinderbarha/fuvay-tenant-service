import React, { useMemo } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";
import type { CustomerContactView } from "../../types/ux05";

/**
 * Minimal-necessary-data customer contact card. No phone number is
 * rendered -- neither Job nor the safe BookingSummary view expose one to
 * staff (see types/ux05.ts CustomerContactView comment); "Call" is
 * therefore not offered as a real action (callSupported is always false
 * until a contact-relay endpoint exists). "Message" opens the real staff
 * chat thread (chatApi) instead.
 *
 * UX-05 Round 7: converted to reactive theme colors.
 */
export function CustomerContactCard({ contact, onMessage }: { contact:CustomerContactView; onMessage?:() => void }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  return (
    <View style={[gs.card, { backgroundColor:colors.surface }, s.card]} testID="customer-contact-card">
      <Text style={[gs.label, { color:colors.textTertiary }]}>Customer</Text>
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

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    card:        { gap:8 },
    name:        { fontSize:theme.font.size.lg, fontWeight:"700", color:colors.textPrimary },
    issue:       { fontSize:theme.font.size.sm, color:colors.textSecondary },
    actions:     { flexDirection:"row", gap:10, marginTop:6 },
    actionBtn:   { flex:1, height:44, borderRadius:theme.radius.md, borderWidth:1, borderColor:colors.border,
                   alignItems:"center", justifyContent:"center" },
    actionText:  { fontSize:theme.font.size.sm, fontWeight:"600", color:colors.textPrimary },
    disabled:    { backgroundColor:colors.surfaceSunken },
    disabledText:{ fontSize:theme.font.size.xs, color:colors.textTertiary },
  });
}
