import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";

/**
 * UX-06 ROUND 2: no real backend contract for saved payment methods was found
 * anywhere in the live openapi.json (searched /v1/payments/customers/*,
 * /v1/*payment*method*). This is consistent with the platform's on-site-payment
 * rule — ServiceOS does not process card payments, so there may be no saved
 * card/UPI feature at all. Per the UX-06 brief's instruction to never invent a
 * contract, this screen was converted to an honest unavailable state rather than
 * calling a guessed endpoint, and is intentionally NOT removed from navigation
 * (kept reachable from Account/Settings) so the gap is visible rather than
 * silently hidden. No card-capture, payout, or bank-transfer UI is shown here or
 * anywhere in this app, per the canonical "no platform payment processing" rule.
 *
 * UX-07 Pass 3b: content/copy untouched (already a correctly-scoped
 * SAFE_INFORMATIONAL_SCREEN per a prior round) -- only the theme import was
 * migrated off the static `theme`/`gs` export onto useTheme().
 */
export function PaymentMethodsScreen() {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  return (
    <View style={[s.screen, s.center]}>
      <Text style={s.icon}>💳</Text>
      <Text style={s.title}>Payment methods aren't managed here</Text>
      <Text style={s.body}>
        ServiceOS jobs are paid on-site directly with your technician — there's
        nothing to save here. If you have platform Service Credit, it's applied
        automatically at checkout.
      </Text>
    </View>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen: { flex:1, backgroundColor:theme.colors.bg },
    center: { flex:1, alignItems:"center", justifyContent:"center", padding:32, gap:12 },
    icon:   { fontSize:44 },
    title:  { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
    body:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center", lineHeight:20 },
  });
}
