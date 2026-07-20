import React, { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";

/**
 * Rendered instead of a restricted screen/section when a StaffPermission is
 * not granted (or role is "technician" for a staff-only surface). This is
 * PRESENTATION ONLY -- hiding a screen here is never itself the security
 * boundary; the backend must independently reject the underlying call.
 *
 * UX-05 Round 5: text/background colors now come from useAppTheme()
 * (reactive light/dark) -- requires a ThemeProvider ancestor. `gs.card`'s
 * shadow/radius/padding stay from the static global styles (shape only,
 * not color -- background is overridden below).
 */
export function PermissionRestrictedState({ reason }: { reason?:string }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  return (
    <View style={[gs.card, s.wrap, { backgroundColor:colors.surface }]} testID="permission-restricted-state"
      accessibilityRole="alert"
      accessibilityLabel={`Restricted. ${reason ?? "You do not have permission to view this."}`}>
      <Text style={s.icon} accessibilityElementsHidden importantForAccessibility="no">🔒</Text>
      <Text style={s.title}>Restricted</Text>
      <Text style={s.reason}>{reason ?? "You do not have permission to view this."}</Text>
    </View>
  );
}

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    wrap:   { alignItems:"center", paddingVertical:40, gap:6 },
    icon:   { fontSize:32 },
    title:  { fontSize:theme.font.size.lg, fontWeight:"700", color:colors.textPrimary },
    reason: { fontSize:theme.font.size.sm, color:colors.textTertiary, textAlign:"center", paddingHorizontal:24 },
  });
}
