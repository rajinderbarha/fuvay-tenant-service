import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { CUSTOMER_STATUS_COLOR, CUSTOMER_STATUS_LABEL } from "../lib/jobStatus";
import { theme } from "../styles/theme";

interface Props { status:string; size?:"sm"|"md" }
export function JobStatusBadge({ status, size="md" }:Props) {
  const c = CUSTOMER_STATUS_COLOR[status] ?? CUSTOMER_STATUS_COLOR.closed;
  const label = CUSTOMER_STATUS_LABEL[status] ?? status.replace(/_/g," ");
  return (
    <View style={[s.badge,{ backgroundColor:c.bg, borderColor:c.border,
      paddingHorizontal:size==="md"?10:7, paddingVertical:size==="md"?4:2 }]}>
      <Text style={[s.text,{ color:c.text, fontSize:size==="md"?theme.font.size.sm:theme.font.size.xs }]}>
        {label}
      </Text>
    </View>
  );
}
const s = StyleSheet.create({ badge:{ borderRadius:99, borderWidth:1, alignSelf:"flex-start" }, text:{ fontWeight:"700" } });
