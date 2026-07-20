import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { JobStatusBadge } from "../JobStatusBadge";
import { PipelineBadge } from "./PipelineBadge";
import type { MyWorkItemView } from "../../types/ux05";

export function WorkItemCard({ item, onPress }: { item:MyWorkItemView; onPress:() => void }) {
  const j = item.job;
  return (
    <TouchableOpacity style={[gs.card, s.card]} activeOpacity={0.85} onPress={onPress} testID="work-item-card"
      accessibilityRole="button"
      accessibilityLabel={`Job ${j.job_number}${j.city ? `, ${j.city}` : ""}, status ${j.status.replace(/_/g," ")}`}>

      <View style={s.top}>
        <View style={{ flex:1 }}>
          <Text style={s.jobNum}>{j.job_number}</Text>
          {j.city && <Text style={s.city}>{j.city}{j.zipcode ? `, ${j.zipcode}` : ""}</Text>}
        </View>
        <JobStatusBadge status={j.status} size="sm" />
      </View>
      <View style={s.bottomRow}>
        <PipelineBadge provenance={item.provenance} compact />
        {item.partsState !== "none" && <Text style={s.chip}>Parts: {item.partsState.replace(/_/g," ")}</Text>}
        {item.offlineCached && <Text style={s.chip}>📴 cached</Text>}
      </View>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  card:      { gap:8 },
  top:       { flexDirection:"row", alignItems:"flex-start", gap:10 },
  jobNum:    { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  city:      { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  bottomRow: { flexDirection:"row", gap:8, alignItems:"center", flexWrap:"wrap" },
  chip:      { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
