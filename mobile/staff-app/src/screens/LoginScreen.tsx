import React, { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View, ActivityIndicator, Alert } from "react-native";
import { useAuth } from "../context/AuthContext";
import { theme } from "../styles/theme";

export function LoginScreen() {
  const [phone,    setPhone]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const { login, error, sessionExpired, clearSessionExpired } = useAuth();

  async function handleLogin() {
    if (!phone.trim() || !password.trim()) {
      Alert.alert("Missing fields", "Please enter phone and password."); return;
    }
    setLoading(true);
    try { await login(phone.trim(), password); clearSessionExpired(); }
    catch { /* error shown via useAuth().error */ }
    finally { setLoading(false); }
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      <View style={s.hero}>
        <View style={s.logoWrap}>
          <Text style={s.logoText}>S</Text>
        </View>
        <Text style={s.appName}>ServiceOS Staff</Text>
        <Text style={s.tagline}>Field Operations App</Text>
      </View>

      <View style={s.form}>
        <Text style={s.formTitle}>Sign In</Text>
        {sessionExpired && !error && (
          <View style={s.sessionBanner}>
            <Text style={s.sessionText}>Your session has ended. Please sign in again.</Text>
          </View>
        )}
        {error && (
          <View style={s.errorBanner}>
            <Text style={s.errorText}>{error}</Text>
          </View>
        )}
        <View style={s.fieldGroup}>
          <Text style={s.fieldLabel}>Phone Number</Text>
          <TextInput
            style={s.input} value={phone} onChangeText={setPhone}
            placeholder="+91 9876543210" placeholderTextColor={theme.colors.textTertiary}
            keyboardType="phone-pad" autoComplete="tel" returnKeyType="next"
          />
        </View>
        <View style={s.fieldGroup}>
          <Text style={s.fieldLabel}>Password</Text>
          <TextInput
            style={s.input} value={password} onChangeText={setPassword}
            placeholder="••••••••" placeholderTextColor={theme.colors.textTertiary}
            secureTextEntry returnKeyType="done" onSubmitEditing={handleLogin}
          />
        </View>
        <TouchableOpacity style={[s.loginBtn, loading && { opacity:0.65 }]}
          onPress={handleLogin} disabled={loading} activeOpacity={0.8}>
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.loginBtnText}>Sign In</Text>}
        </TouchableOpacity>
        <Text style={s.hint}>Contact your manager if you forgot your password.</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  screen:     { flex:1, backgroundColor:theme.colors.brand },
  hero:       { flex:1, alignItems:"center", justifyContent:"center", gap:10 },
  logoWrap:   { width:72, height:72, borderRadius:20, backgroundColor:"rgba(255,255,255,0.15)",
                alignItems:"center", justifyContent:"center" },
  logoText:   { fontSize:36, fontWeight:"800", color:"#fff" },
  appName:    { fontSize:theme.font.size.xxxl, fontWeight:"800", color:"#fff", letterSpacing:-0.5 },
  tagline:    { fontSize:theme.font.size.base, color:"rgba(255,255,255,0.65)" },
  form:       { backgroundColor:theme.colors.surface, borderTopLeftRadius:28, borderTopRightRadius:28,
                padding:theme.spacing.xl, paddingBottom:48, gap:16 },
  formTitle:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  errorBanner:{ backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md, padding:12,
                borderWidth:1, borderColor:theme.colors.dangerBorder },
  errorText:  { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
  sessionBanner:{ backgroundColor:theme.colors.warningBg, borderRadius:theme.radius.md, padding:12,
                borderWidth:1, borderColor:theme.colors.warningBorder },
  sessionText:{ fontSize:theme.font.size.sm, color:theme.colors.warningText },
  fieldGroup: { gap:6 },
  fieldLabel: { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
  input:      { height:48, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                paddingHorizontal:14, fontSize:theme.font.size.md, color:theme.colors.textPrimary,
                backgroundColor:theme.colors.surfaceSunken },
  loginBtn:   { height:52, backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg,
                alignItems:"center", justifyContent:"center", marginTop:4 },
  loginBtnText:{ fontSize:theme.font.size.lg, fontWeight:"700", color:"#fff" },
  hint:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
});
