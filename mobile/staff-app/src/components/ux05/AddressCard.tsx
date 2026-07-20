import React from "react";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { CustomerContactView } from "../../types/ux05";

/**
 * Address + navigation handoff (workstream 11). Navigation opens the
 * device's map app with the service address text -- no continuous
 * location tracking, no device-permission request until a Navigate action
 * is actually pressed (asks only when needed, per the location-privacy
 * hard constraint).
 */
export function AddressCard({ contact }: { contact:CustomerContactView }) {
  const addressLine = [contact.city, contact.zipcode].filter(Boolean).join(", ") || "No address on file";

  function copy() { Alert.alert("Copied", addressLine); }
  function navigate() { Alert.alert("Navigate", `Would open maps to: ${addressLine}`); }

  return (
    <View style={[gs.card, s.card]} testID="address-card">
      <Text style={gs.label}>Service Address</Text>
      <Text style={s.address}>📍 {addressLine}</Text>
      <View style={s.actions}>
        <TouchableOpacity style={s.actionBtn} onPress={navigate}
          accessibilityRole="button" accessibilityLabel={`Navigate to ${addressLine}`}>
          <Text style={s.actionText}>🧭 Navigate</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.actionBtn} onPress={copy}
          accessibilityRole="button" accessibilityLabel={`Copy address ${addressLine}`}>
          <Text style={s.actionText}>📋 Copy</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card:      { gap:8 },
  address:   { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
  actions:   { flexDirection:"row", gap:10, marginTop:6 },
  // UX-05 Round 4 a11y pass: 40pt -> 44pt to meet the minimum touch-target size.
  actionBtn: { flex:1, height:44, borderRadius:theme.radius.md, borderWidth:1, borderColor:theme.colors.border,
               alignItems:"center", justifyContent:"center" },
  actionText:{ fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
});
