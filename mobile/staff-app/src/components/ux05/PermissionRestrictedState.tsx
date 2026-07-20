import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";

/**
 * Rendered instead of a restricted screen/section when a StaffPermission is
 * not granted (or role is "technician" for a staff-only surface). This is
 * PRESENTATION ONLY -- hiding a screen here is never itself the security
 * boundary; the backend must independently reject the underlying call.
 */
export function PermissionRestrictedState({ reason }: { reason?:string }) {
  return (
    <View style={[gs.card, s.wrap]} testID="permission-restricted-state">
      <Text style={s.icon}>🔒</Text>
      <Text style={s.title}>Restricted</Text>
      <Text style={s.reason}>{reason ?? "You do not have permission to view this."}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  wrap:   { alignItems:"center", paddingVertical:40, gap:6 },
  icon:   { fontSize:32 },
  title:  { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
  reason: { fontSize:theme.font.size.sm, color:theme.colors.textTertiary, textAlign:"center", paddingHorizontal:24 },
});
