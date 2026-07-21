import React, { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";

/**
 * UX-06 ROUND 1: rewritten to use the real, verified backend contract —
 * POST /v1/auth/login (email + password), the SAME unified login endpoint every
 * role uses. The prior scaffold's phone/OTP flow called two endpoints
 * (/v1/auth/customer/otp-request, /v1/auth/customer/otp-verify) that do not exist
 * in the live backend — removed rather than shipped as a dead control.
 * See docs/design/ux-06-customer-app/customer-authentication.md.
 *
 * UX-07 Round 4 Pass 2: migrated to useTheme() for dark mode (hero stays on
 * the brand color in both modes for contrast/branding continuity; the sheet
 * and inputs follow surface/border tokens). Added input labels (accessible
 * name distinct from the placeholder, since placeholders are not a reliable
 * accessible name on all platforms), error-region semantics, and a 44px+
 * submit target.
 */
export function LoginScreen() {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const { login, error } = useAuth();
  const { theme } = useTheme();
  const s = makeStyles(theme);

  async function handleLogin() {
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    try { await login(email.trim(), password); }
    finally { setLoading(false); }
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      <View style={s.hero}>
        <View style={s.logo}><Text style={s.logoText}>⚡</Text></View>
        <Text style={s.appName}>ServiceOS</Text>
        <Text style={s.tagline}>Home services, on demand</Text>
      </View>

      <View style={s.sheet}>
        {error && <View style={s.errBox} accessibilityRole="alert" accessible><Text style={s.errText}>{error}</Text></View>}

        <Text style={s.formTitle}>Sign in</Text>
        <Text style={s.fieldLabel} nativeID="login-email-label">Email</Text>
        <TextInput style={s.input} value={email} onChangeText={setEmail}
          placeholder="you@example.com" placeholderTextColor={theme.colors.textTertiary}
          keyboardType="email-address" autoCapitalize="none" testID="login-email"
          accessibilityLabel="Email address" accessibilityLabelledBy="login-email-label" />
        <Text style={s.fieldLabel} nativeID="login-password-label">Password</Text>
        <TextInput style={s.input} value={password} onChangeText={setPassword}
          placeholder="Password" placeholderTextColor={theme.colors.textTertiary}
          secureTextEntry testID="login-password"
          accessibilityLabel="Password" accessibilityLabelledBy="login-password-label" />
        <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading} activeOpacity={0.8} testID="login-submit"
          accessible accessibilityRole="button" accessibilityLabel="Sign in" accessibilityState={{ disabled: loading, busy: loading }}>
          {loading ? <ActivityIndicator color={theme.colors.textInverse}/> : <Text style={s.btnText}>Sign In →</Text>}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:   { flex:1, backgroundColor:theme.colors.brand },
    hero:     { flex:1, alignItems:"center", justifyContent:"center", gap:10, paddingBottom:24 },
    logo:     { width:80, height:80, borderRadius:24, backgroundColor:"rgba(255,255,255,0.18)",
                alignItems:"center", justifyContent:"center" },
    logoText: { fontSize:40 },
    appName:  { fontSize:theme.font.size.huge, fontWeight:"800", color:theme.colors.textInverse, letterSpacing:-1 },
    tagline:  { fontSize:theme.font.size.base, color:"rgba(255,255,255,0.7)" },
    sheet:    { backgroundColor:theme.colors.surface, borderTopLeftRadius:32, borderTopRightRadius:32,
                padding:24, paddingBottom:48, gap:8 },
    formTitle:{ fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary, marginBottom:6 },
    fieldLabel:{ fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.textSecondary, marginTop:4 },
    errBox:   { backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md, padding:12,
                borderWidth:1, borderColor:theme.colors.dangerBorder },
    errText:  { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
    input:    { height:50, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                paddingHorizontal:16, fontSize:theme.font.size.md, color:theme.colors.textPrimary,
                backgroundColor:theme.colors.surfaceSunken },
    btn:      { height:52, minHeight:44, backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg,
                alignItems:"center", justifyContent:"center", marginTop:8 },
    btnText:  { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textInverse },
  });
}
