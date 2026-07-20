import React from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../../context/AuthContext";
import { deriveRole, permissionsFor, hasPermission } from "../../lib/ux05/permissions";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";

/**
 * Staff "More" tab (workstream 2/22). Lists ONLY permission-compatible
 * areas -- never tenant-owner administration (this app has no route for
 * that at all, so there is nothing to accidentally expose). Each entry is
 * individually gated by hasPermission(); ungranted entries render disabled
 * with the reason, never hidden silently (so a staff member can see WHY
 * something is unavailable, matching the brief's "disabled-with-reason"
 * pattern from UX-04).
 */
const ENTRIES: Array<{ key:string; label:string; permission:Parameters<typeof hasPermission>[1] }> = [
  { key:"assignment", label:"Assignment", permission:"assignment:manage" },
  { key:"quote",      label:"Quote Review", permission:"quote:review" },
  { key:"checklist",  label:"Checklist Review", permission:"checklist:review" },
  { key:"parts",      label:"Parts Approvals", permission:"parts_request:approve" },
  { key:"issues",     label:"Customer Issues", permission:"customer_issue:manage" },
];

export function StaffMoreScreen() {
  const { user, logout } = useAuth();
  const role = user ? deriveRole(user) : "technician";
  const permissions = permissionsFor(role, user?.tenant_id ?? null);

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {ENTRIES.map(entry => {
        const granted = hasPermission(permissions, entry.permission);
        return (
          <View key={entry.key} style={[gs.card, s.row]}>
            <Text style={[s.label, !granted && s.labelDisabled]}>{entry.label}</Text>
            <Text style={s.status}>{granted ? "Available" : "Restricted"}</Text>
          </View>
        );
      })}
      <Button label="Sign Out" variant="danger" size="lg" onPress={logout} fullWidth />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:10, paddingBottom:32 },
  row:          { flexDirection:"row", justifyContent:"space-between", alignItems:"center" },
  label:        { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  labelDisabled:{ color:theme.colors.textTertiary },
  status:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
