import React, { useMemo } from "react";
import { Alert, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";
import type { CustomerContactView } from "../../types/ux05";

/**
 * Address + navigation handoff (workstream 11). Navigation opens the
 * device's map app with the service address text -- no continuous
 * location tracking, no device-permission request until a Navigate action
 * is actually pressed (asks only when needed, per the location-privacy
 * hard constraint).
 *
 * UX-05 Round 7: converted to reactive theme colors.
 */
export function AddressCard({ contact }: { contact:CustomerContactView }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  const addressLine = [contact.city, contact.zipcode].filter(Boolean).join(", ") || "No address on file";

  function copy() { Alert.alert("Copied", addressLine); }
  function navigate() { Alert.alert("Navigate", `Would open maps to: ${addressLine}`); }

  return (
    <View style={[gs.card, { backgroundColor:colors.surface }, s.card]} testID="address-card">
      <Text style={[gs.label, { color:colors.textTertiary }]}>Service Address</Text>
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

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    card:      { gap:8 },
    address:   { fontSize:theme.font.size.base, color:colors.textPrimary },
    actions:   { flexDirection:"row", gap:10, marginTop:6 },
    actionBtn: { flex:1, height:44, borderRadius:theme.radius.md, borderWidth:1, borderColor:colors.border,
                 alignItems:"center", justifyContent:"center" },
    actionText:{ fontSize:theme.font.size.sm, fontWeight:"600", color:colors.textPrimary },
  });
}
