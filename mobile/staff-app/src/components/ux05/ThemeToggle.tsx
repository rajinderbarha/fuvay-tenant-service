import React, { useMemo } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { useAppTheme, type ThemePreference } from "../../context/ThemeContext";

const OPTIONS: Array<{ key:ThemePreference; label:string }> = [
  { key:"light", label:"Light" }, { key:"dark", label:"Dark" }, { key:"system", label:"System" },
];

/**
 * Real theme preference control -- writes through useAppTheme().setPreference,
 * which persists to AsyncStorage and immediately re-resolves every consuming
 * component (see ThemeContext.tsx). Not a design fixture; this is the real
 * production control.
 */
export function ThemeToggle() {
  const { preference, scheme, setPreference } = useAppTheme();
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  return (
    <View style={[gs.card, { backgroundColor:colors.surface, gap:10 }]} testID="theme-toggle">
      <Text style={[gs.label, { color:colors.textTertiary }]}>Appearance</Text>
      <View style={s.row}>
        {OPTIONS.map(opt => (
          <TouchableOpacity key={opt.key}
            style={[s.chip, preference===opt.key && s.chipActive]}
            onPress={() => setPreference(opt.key)}
            accessibilityRole="button" accessibilityLabel={`Set appearance to ${opt.label}`}
            accessibilityState={{ selected: preference===opt.key }}>
            <Text style={[s.chipText, preference===opt.key && s.chipTextActive]}>{opt.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <Text style={s.resolved}>Currently showing: {scheme}</Text>
    </View>
  );
}

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    row:          { flexDirection:"row", gap:8 },
    chip:         { flex:1, paddingVertical:10, borderRadius:theme.radius.md, borderWidth:1, borderColor:colors.border,
                    alignItems:"center", justifyContent:"center", minHeight:44 },
    chipActive:   { backgroundColor:colors.accentLight, borderColor:colors.accent },
    chipText:     { fontSize:theme.font.size.sm, fontWeight:"600", color:colors.textPrimary },
    chipTextActive:{ color:colors.accent },
    resolved:     { fontSize:theme.font.size.xs, color:colors.textTertiary },
  });
}
