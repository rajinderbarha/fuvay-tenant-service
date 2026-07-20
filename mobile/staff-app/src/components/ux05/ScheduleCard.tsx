import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { JobStatusBadge } from "../JobStatusBadge";
import type { ScheduleItemView } from "../../types/ux05";

export function ScheduleCard({ item, onPress }: { item:ScheduleItemView; onPress:() => void }) {
  return (
    <TouchableOpacity style={[gs.card, s.card]} activeOpacity={0.85} onPress={onPress} testID="schedule-card">
      <View style={s.row}>
        <Text style={s.time}>{item.timeWindow ?? "No time set"}</Text>
        {item.hasConflict && <Text style={s.conflict}>⚠ Conflict</Text>}
      </View>
      <View style={[s.row, { marginTop:4 }]}>
        <Text style={s.jobNum}>{item.job.job_number}</Text>
        <JobStatusBadge status={item.status} size="sm" />
      </View>
      {item.job.city && <Text style={s.city}>{item.job.city}</Text>}
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  card:    { gap:4 },
  row:     { flexDirection:"row", justifyContent:"space-between", alignItems:"center" },
  time:    { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.accent },
  conflict:{ fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.dangerText },
  jobNum:  { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  city:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
});
