import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";

/**
 * Dev-only showcase covering generic system states referenced throughout
 * the brief but not yet built as dedicated production screens: Session
 * Expired, Tenant Suspended, Read-only, Restricted. These are reusable
 * presentation patterns, not fixtures tied to one workflow -- kept in one
 * showcase rather than four near-identical files.
 *
 * None of these are wired to a real trigger (no live session-expiry event,
 * no live tenant-suspension flag) -- all MOCK_DESIGN_ONLY, demonstrating
 * the intended screen content only.
 */
export function SystemStatesShowcaseScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="system-states-showcase">
      <View style={[gs.card, s.block]}>
        <Text style={s.icon}>⏱</Text>
        <Text style={s.title}>Session Expired</Text>
        <Text style={s.body}>Your session has ended for security. Sign in again to continue.</Text>
        <Button label="Sign In Again" variant="primary" fullWidth onPress={() => {}} />
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- not wired to a real token-expiry event yet.</Text>
      </View>

      <View style={[gs.card, s.block]}>
        <Text style={s.icon}>🚫</Text>
        <Text style={s.title}>Tenant Suspended</Text>
        <Text style={s.body}>
          This tenant account is currently suspended. You cannot view or update jobs until it's reactivated.
          Contact your administrator for details.
        </Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- not wired to a real tenant-status field yet.</Text>
      </View>

      <View style={[gs.card, s.block]}>
        <Text style={s.icon}>👁</Text>
        <Text style={s.title}>Read-only</Text>
        <Text style={s.body}>
          This job is read-only -- it was completed or transferred, so no further changes can be made from here.
        </Text>
        <Text style={s.mockNote}>Example presentation only; real read-only state is job-status-driven where it already exists (e.g. a completed ServiceJob).</Text>
      </View>

      <View style={[gs.card, { padding:0 }]}>
        <Text style={s.title2}>Restricted</Text>
        <PermissionRestrictedState reason="Example: this account does not hold the required StaffPermission." />
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:  { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  block:    { alignItems:"center", gap:8, paddingVertical:20 },
  icon:     { fontSize:32 },
  title:    { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
  title2:   { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary, padding:theme.spacing.base, paddingBottom:0 },
  body:     { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center" },
  mockNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
});
