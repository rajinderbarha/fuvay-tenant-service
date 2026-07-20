import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../../context/AuthContext";
import { deriveRole, permissionsFor } from "../../lib/ux05/permissions";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";
import { theme, gs } from "../../styles/theme";

/**
 * Staff Home (workstream 4). API_CONTRACT_REQUIRED: no staff work-queue
 * summary endpoint exists (see backend-contract-blockers.md), and
 * deriveRole() fails closed to "technician" for every real user today
 * (no live role field on StaffUser) -- so in the real app, a user reaching
 * this screen at all would already indicate role:"staff" was set somewhere
 * real. Until that's confirmed, this screen honestly renders the
 * permission-restricted state rather than fabricating queue counts.
 */
export function StaffHomeScreen() {
  const { user } = useAuth();
  const role = user ? deriveRole(user) : "technician";
  const permissions = permissionsFor(role, user?.tenant_id ?? null);
  const anyGranted = permissions.some(p => p.granted);

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      <View style={[gs.card, { gap:6 }]}>
        <Text style={gs.label}>Staff Home</Text>
        <Text style={s.note}>
          Your staff dashboard is coming soon. We're not able to show live counts here yet, so nothing below is
          real data — check back once this is ready.
        </Text>
      </View>
      {!anyGranted && (
        <PermissionRestrictedState reason="No StaffPermission grants are confirmed for this account yet (no live permission endpoint wired up)." />
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  note:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:20 },
});
