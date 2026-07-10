import React, { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../lib/api";
import { theme } from "../styles/theme";

type Mode = "phone" | "otp" | "email";

export function LoginScreen() {
  const [mode,      setMode]      = useState<Mode>("phone");
  const [phone,     setPhone]     = useState("");
  const [otp,       setOtp]       = useState("");
  const [email,     setEmail]     = useState("");
  const [password,  setPassword]  = useState("");
  const [sessionId, setSessionId] = useState("");
  const [loading,   setLoading]   = useState(false);
  const { loginOtp, loginEmail, error } = useAuth();

  async function handleRequestOtp() {
    if (!phone.trim()) return;
    setLoading(true);
    try {
      const { session_id } = await authApi.requestOtp(phone.trim());
      setSessionId(session_id); setMode("otp");
    } catch(e:unknown) { /* error shown via useAuth */ }
    finally { setLoading(false); }
  }

  async function handleVerifyOtp() {
    if (!otp.trim()) return;
    setLoading(true);
    try { await loginOtp(phone, otp.trim(), sessionId); }
    finally { setLoading(false); }
  }

  async function handleEmailLogin() {
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    try { await loginEmail(email.trim(), password); }
    finally { setLoading(false); }
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      {/* Hero */}
      <View style={s.hero}>
        <View style={s.logo}><Text style={s.logoText}>⚡</Text></View>
        <Text style={s.appName}>ServiceOS</Text>
        <Text style={s.tagline}>Home services, on demand</Text>
      </View>

      {/* Form */}
      <View style={s.sheet}>
        {error && <View style={s.errBox}><Text style={s.errText}>{error}</Text></View>}

        {mode === "phone" && (
          <>
            <Text style={s.formTitle}>Enter your phone number</Text>
            <TextInput style={s.input} value={phone} onChangeText={setPhone}
              placeholder="+91 9876543210" placeholderTextColor={theme.colors.textTertiary}
              keyboardType="phone-pad" autoFocus />
            <TouchableOpacity style={s.btn} onPress={handleRequestOtp} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator color="#fff"/> : <Text style={s.btnText}>Send OTP →</Text>}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setMode("email")} style={{ alignItems:"center", marginTop:12 }}>
              <Text style={s.linkText}>Use email instead</Text>
            </TouchableOpacity>
          </>
        )}

        {mode === "otp" && (
          <>
            <Text style={s.formTitle}>Enter OTP</Text>
            <Text style={s.sub}>Sent to {phone}</Text>
            <TextInput style={[s.input,s.otpInput]} value={otp} onChangeText={setOtp}
              placeholder="------" placeholderTextColor={theme.colors.textTertiary}
              keyboardType="number-pad" maxLength={6} autoFocus />
            <TouchableOpacity style={s.btn} onPress={handleVerifyOtp} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator color="#fff"/> : <Text style={s.btnText}>Verify OTP →</Text>}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => { setMode("phone"); setOtp(""); }} style={{ alignItems:"center",marginTop:12 }}>
              <Text style={s.linkText}>← Change number</Text>
            </TouchableOpacity>
          </>
        )}

        {mode === "email" && (
          <>
            <Text style={s.formTitle}>Sign in with email</Text>
            <TextInput style={s.input} value={email} onChangeText={setEmail}
              placeholder="you@example.com" placeholderTextColor={theme.colors.textTertiary}
              keyboardType="email-address" autoCapitalize="none" />
            <TextInput style={s.input} value={password} onChangeText={setPassword}
              placeholder="Password" placeholderTextColor={theme.colors.textTertiary}
              secureTextEntry />
            <TouchableOpacity style={s.btn} onPress={handleEmailLogin} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator color="#fff"/> : <Text style={s.btnText}>Sign In →</Text>}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setMode("phone")} style={{ alignItems:"center",marginTop:12 }}>
              <Text style={s.linkText}>Use phone OTP instead</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  screen:   { flex:1, backgroundColor:theme.colors.brand },
  hero:     { flex:1, alignItems:"center", justifyContent:"center", gap:10, paddingBottom:24 },
  logo:     { width:80, height:80, borderRadius:24, backgroundColor:"rgba(255,255,255,0.18)",
              alignItems:"center", justifyContent:"center" },
  logoText: { fontSize:40 },
  appName:  { fontSize:theme.font.size.huge, fontWeight:"800", color:"#fff", letterSpacing:-1 },
  tagline:  { fontSize:theme.font.size.base, color:"rgba(255,255,255,0.65)" },
  sheet:    { backgroundColor:theme.colors.surface, borderTopLeftRadius:32, borderTopRightRadius:32,
              padding:24, paddingBottom:48, gap:14 },
  formTitle:{ fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  sub:      { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:-6 },
  errBox:   { backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md, padding:12,
              borderWidth:1, borderColor:theme.colors.dangerBorder },
  errText:  { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
  input:    { height:50, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
              paddingHorizontal:16, fontSize:theme.font.size.md, color:theme.colors.textPrimary,
              backgroundColor:theme.colors.surfaceSunken },
  otpInput: { fontSize:theme.font.size.xxxl, letterSpacing:8, textAlign:"center" },
  btn:      { height:52, backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg,
              alignItems:"center", justifyContent:"center" },
  btnText:  { fontSize:theme.font.size.lg, fontWeight:"700", color:"#fff" },
  linkText: { fontSize:theme.font.size.sm, color:theme.colors.accent, fontWeight:"600" },
});
