import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";

const GROUPS = [
  "Unassigned", "Assignment Conflict", "Quote Review", "Checklist Review",
  "Parts Approval", "Customer Issue", "SLA Risk", "Work Done Awaiting Completion",
];

/**
 * Staff Work Queue (workstream 6). Same honesty pattern as StaffHomeScreen
 * -- no live work-queue endpoint exists, so this renders the intended
 * group structure with a restricted-state notice rather than a fabricated
 * list.
 */
export function StaffWorkQueueScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      <View style={[gs.card, { gap:6 }]}>
        <Text style={s.note}>MOCK_DESIGN_ONLY: intended group structure shown below, no live data source yet.</Text>
      </View>
      {GROUPS.map(g => (
        <View key={g} style={[gs.card, s.groupRow]}>
          <Text style={s.groupLabel}>{g}</Text>
        </View>
      ))}
      <PermissionRestrictedState reason="assignment:manage / quote:review / checklist:review / parts_request:approve / customer_issue:manage are not confirmed granted." />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:   { padding:theme.spacing.base, gap:10, paddingBottom:32 },
  note:      { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  groupRow:  { flexDirection:"row", justifyContent:"space-between" },
  groupLabel:{ fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
});
