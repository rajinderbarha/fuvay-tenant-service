import React from "react";
import { StyleSheet, Text, View, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

interface Props { label:string; value:string; sub?:string; accent?:string; style?:ViewStyle }

export function StatCard({ label, value, sub, accent, style }: Props) {
  return (
    <View style={[s.card, style]}>
      <Text style={s.label}>{label}</Text>
      <Text style={[s.value, accent ? { color:accent } : {}]}>{value}</Text>
      {sub && <Text style={s.sub}>{sub}</Text>}
    </View>
  );
}

const s = StyleSheet.create({
  card:  { backgroundColor:theme.colors.surfaceSunken, borderRadius:theme.radius.md,
           padding:theme.spacing.md, alignItems:"center", flex:1 },
  label: { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.textTertiary,
           textTransform:"uppercase", letterSpacing:0.6, marginBottom:4 },
  value: { fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.textPrimary },
  sub:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
});
