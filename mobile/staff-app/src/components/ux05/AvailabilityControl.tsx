import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { AvailabilityView } from "../../types/ux05";

const OPTIONS: Array<{ key:AvailabilityView["workStatus"]; label:string }> = [
  { key:"available", label:"Available" }, { key:"busy", label:"Busy" },
  { key:"on_job", label:"On Job" }, { key:"off_duty", label:"Off Duty" },
];

/**
 * Availability / work-status control (workstream 21). Checked lib/api.ts:
 * StaffUser carries `status` (account status, e.g. "active") and Job
 * carries its own `status` -- neither is a dedicated available/busy/on_job/
 * off_duty work-status field. No such endpoint exists. This renders the
 * intended control with all options selectable (local state only) and
 * explicitly labels the other two statuses as distinct, non-invented
 * concepts (account status is real and shown as-is; job status is real and
 * shown as-is; work status is the only MOCK_DESIGN_ONLY piece here).
 */
export function AvailabilityControl({ availability, onChange }: {
  availability:AvailabilityView; onChange:(status:AvailabilityView["workStatus"]) => void;
}) {
  return (
    <View style={[gs.card, { gap:10 }]} testID="availability-control">
      <Text style={gs.label}>Work Status</Text>
      <View style={s.row}>
        {OPTIONS.map(opt => (
          <TouchableOpacity key={opt.key}
            style={[s.chip, availability.workStatus===opt.key && s.chipActive]}
            onPress={() => onChange(opt.key)}
            accessibilityRole="button" accessibilityState={{ selected: availability.workStatus===opt.key }}>
            <Text style={[s.chipText, availability.workStatus===opt.key && s.chipTextActive]}>{opt.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={s.distinctRow}>
        <Text style={s.distinctLabel}>Account status: <Text style={s.distinctValue}>{availability.accountStatus}</Text></Text>
        {availability.currentJobStatus && (
          <Text style={s.distinctLabel}>Current job status: <Text style={s.distinctValue}>{availability.currentJobStatus}</Text></Text>
        )}
      </View>
      <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live work-status endpoint exists; selection is local-state only.</Text>
    </View>
  );
}

const s = StyleSheet.create({
  row:          { flexDirection:"row", flexWrap:"wrap", gap:8 },
  chip:         { paddingHorizontal:14, paddingVertical:10, borderRadius:theme.radius.md, borderWidth:1, borderColor:theme.colors.border, minHeight:44, justifyContent:"center" },
  chipActive:   { backgroundColor:theme.colors.accentLight, borderColor:theme.colors.accent },
  chipText:     { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
  chipTextActive:{ color:theme.colors.accent },
  distinctRow:  { gap:2 },
  distinctLabel:{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  distinctValue:{ color:theme.colors.textPrimary, fontWeight:"600" },
  mockNote:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
