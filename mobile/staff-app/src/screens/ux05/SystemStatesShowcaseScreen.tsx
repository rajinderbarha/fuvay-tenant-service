import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import { Button } from "../../components/Button";
import { PermissionRestrictedState } from "../../components/ux05/PermissionRestrictedState";

/**
 * Dev-only showcase covering generic system states referenced throughout
 * the brief: Session Expired, Tenant Suspended, Account Disabled,
 * Reauthentication Required, Read-only, Restricted. These are reusable
 * presentation patterns, not fixtures tied to one workflow -- kept in one
 * showcase rather than six near-identical files.
 *
 * UX-05 Round 7: Session Expired is now a REAL, wired state (see
 * AuthContext.tsx's sessionExpired, driven by a genuine 401 on the app's
 * initial /me check) -- the real LoginScreen shows this banner today, not
 * a mockup. The card below is a static illustration of that same real copy
 * for showcase-browsing purposes, not a duplicate implementation. Tenant
 * Suspended / Account Disabled / Reauthentication Required / Read-only /
 * Restricted remain MOCK_DESIGN_ONLY -- no live tenant-status or
 * account-status-beyond-`StaffUser.status` field exists to drive them for
 * real yet.
 */
export function SystemStatesShowcaseScreen() {
  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="system-states-showcase">
      <View style={[gs.card, s.block]}>
        <Text style={s.icon}>⏱</Text>
        <Text style={s.title}>Session Expired</Text>
        <Text style={s.body}>Your session has ended. Please sign in again.</Text>
        <Button label="Sign In Again" variant="primary" fullWidth onPress={() => {}} />
        <Text style={s.realNote}>REAL -- this exact copy is shown on the actual LoginScreen when AuthContext detects a genuine 401 on app start (see AuthContext.tsx).</Text>
      </View>

      <View style={[gs.card, s.block]}>
        <Text style={s.icon}>🔐</Text>
        <Text style={s.title}>Reauthentication Required</Text>
        <Text style={s.body}>
          For your security, please confirm your password to continue this action.
        </Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no action in this app currently requires step-up reauthentication; no live trigger exists.</Text>
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
        <Text style={s.icon}>⛔</Text>
        <Text style={s.title}>Account Disabled</Text>
        <Text style={s.body}>
          Your account has been disabled by your tenant administrator. Contact them to restore access.
        </Text>
        <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- StaffUser.status is real (e.g. "active"), but no disabled-account value or 403-on-login path was confirmed against the real backend this round.</Text>
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
  realNote: { fontSize:theme.font.size.xs, color:theme.colors.successText, textAlign:"center", fontWeight:"700" },
});
