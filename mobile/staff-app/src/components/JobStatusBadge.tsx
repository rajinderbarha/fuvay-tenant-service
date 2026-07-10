import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { STATUS_COLOR, STATUS_LABEL } from "../lib/transitions";
import { theme } from "../styles/theme";

interface Props { status:string; size?:"sm"|"md" }

export function JobStatusBadge({ status, size="md" }: Props) {
  const c = STATUS_COLOR[status] ?? STATUS_COLOR.cancelled;
  const label = STATUS_LABEL[status] ?? status.replace(/_/g," ");
  const isLg = size === "md";
  return (
    <View style={[s.badge, { backgroundColor:c.bg, borderColor:c.border, paddingHorizontal:isLg?10:7, paddingVertical:isLg?4:2 }]}>
      <Text style={[s.text, { color:c.text, fontSize:isLg?theme.font.size.sm:theme.font.size.xs }]}>
        {label}
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  badge:{ borderRadius:999, borderWidth:1, alignSelf:"flex-start" },
  text: { fontWeight:"700", letterSpacing:0.3 },
});
