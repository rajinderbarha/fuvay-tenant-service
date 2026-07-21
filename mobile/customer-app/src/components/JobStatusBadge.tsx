import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { CUSTOMER_STATUS_COLOR, CUSTOMER_STATUS_COLOR_DARK, CUSTOMER_STATUS_LABEL } from "../lib/jobStatus";
import { useTheme } from "../context/ThemeContext";

interface Props { status:string; size?:"sm"|"md" }
// UX-07 Round 4 Pass 2: picks the dark-mode status palette when active, and
// exposes the status as an accessible text label (not color alone) via
// accessibilityLabel -- the label text is already rendered, this makes the
// "Status: <label>" semantic explicit for screen readers.
export function JobStatusBadge({ status, size="md" }:Props) {
  const { mode, theme } = useTheme();
  const palette = mode === "dark" ? CUSTOMER_STATUS_COLOR_DARK : CUSTOMER_STATUS_COLOR;
  const fallback = mode === "dark" ? CUSTOMER_STATUS_COLOR_DARK.closed : CUSTOMER_STATUS_COLOR.closed;
  const c = palette[status] ?? fallback;
  const label = CUSTOMER_STATUS_LABEL[status] ?? status.replace(/_/g," ");
  return (
    <View accessible accessibilityLabel={`Status: ${label}`}
      style={[s.badge,{ backgroundColor:c.bg, borderColor:c.border,
      paddingHorizontal:size==="md"?10:7, paddingVertical:size==="md"?4:2 }]}>
      <Text style={[s.text,{ color:c.text, fontSize:size==="md"?theme.font.size.sm:theme.font.size.xs }]}>
        {label}
      </Text>
    </View>
  );
}
const s = StyleSheet.create({ badge:{ borderRadius:99, borderWidth:1, alignSelf:"flex-start" }, text:{ fontWeight:"700" } });
