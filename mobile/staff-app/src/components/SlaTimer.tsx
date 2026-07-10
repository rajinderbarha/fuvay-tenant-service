import React, { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { getSlaStatus } from "../lib/transitions";
import { theme } from "../styles/theme";

interface Props { slaMinutes:number; minutesInStatus:number }

export function SlaTimer({ slaMinutes, minutesInStatus }: Props) {
  const overdue = minutesInStatus - slaMinutes;
  const sla     = getSlaStatus(overdue);
  const remaining = slaMinutes - minutesInStatus;

  return (
    <View style={[s.wrap, { backgroundColor:sla.color + "20", borderColor:sla.color + "60" }]}>
      <View style={[s.dot, { backgroundColor:sla.color }]} />
      <Text style={[s.text, { color:sla.color }]}>
        {overdue > 0 ? `${overdue}m overdue · ${sla.label}` : `${remaining}m left · ${sla.label}`}
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flexDirection:"row", alignItems:"center", gap:6, paddingHorizontal:10, paddingVertical:5, borderRadius:99, borderWidth:1 },
  dot:  { width:6, height:6, borderRadius:3 },
  text: { fontSize:theme.font.size.xs, fontWeight:"700" },
});
