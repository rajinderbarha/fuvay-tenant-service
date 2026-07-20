import React, { useMemo } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { useAppTheme } from "../../context/ThemeContext";
import { JobStatusBadge } from "../JobStatusBadge";
import type { ScheduleItemView } from "../../types/ux05";

/** UX-05 Round 7: reactive theme colors -- requires a ThemeProvider ancestor. */
export function ScheduleCard({ item, onPress }: { item:ScheduleItemView; onPress:() => void }) {
  const { colors } = useAppTheme();
  const s = useMemo(() => makeStyles(colors), [colors]);
  return (
    <TouchableOpacity style={[gs.card, { backgroundColor:colors.surface }, s.card]} activeOpacity={0.85} onPress={onPress} testID="schedule-card"
      accessibilityRole="button"
      accessibilityLabel={`${item.timeWindow ?? "No time set"}, job ${item.job.job_number}${item.hasConflict ? ", schedule conflict" : ""}`}>

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

function makeStyles(colors: ReturnType<typeof import("../../styles/theme").getColors>) {
  return StyleSheet.create({
    card:    { gap:4 },
    row:     { flexDirection:"row", justifyContent:"space-between", alignItems:"center" },
    time:    { fontSize:theme.font.size.sm, fontWeight:"700", color:colors.accent },
    conflict:{ fontSize:theme.font.size.xs, fontWeight:"700", color:colors.dangerText },
    jobNum:  { fontSize:theme.font.size.base, fontWeight:"700", color:colors.textPrimary },
    city:    { fontSize:theme.font.size.sm, color:colors.textSecondary },
  });
}
