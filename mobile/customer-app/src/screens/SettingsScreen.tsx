import React from "react";
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { theme, gs } from "../styles/theme";

/**
 * UX-06 ROUND 2 correction:
 *
 * 1. The prior scaffold's app-wide "Language" chip selector (English/Hindi/
 *    Marathi/Tamil/Telugu, saved via a fake /v1/settings/{id}/preferences
 *    endpoint) has been REMOVED, not just re-pointed. Per the UX-06 brief's
 *    hard language-architecture rule, ordinary app screens stay in a single
 *    base language permanently — an app-wide language selector here would be a
 *    direct violation. Multilingual behavior belongs exclusively inside the
 *    DeepSeek chat (see chat-language-selection.md).
 * 2. No confirmed real request/response schema for saving notification
 *    preferences was found this round (GET /v1/customer/notifications/preferences
 *    exists but its PUT/POST counterpart and exact field shape weren't verified),
 *    so the notification toggles are shown as an honest "coming soon" note
 *    rather than wired to a guessed endpoint.
 * 3. Sign out (real, uses AuthContext.logout -> POST /v1/auth/logout) and the
 *    static Privacy/Terms links are kept — no backend contract needed for those.
 */
export function SettingsScreen() {
  const { logout } = useAuth();

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      <Text style={gs.sectionTitle}>Notification Preferences</Text>
      <View style={s.comingSoon}>
        <Text style={{fontSize:28}}>🚧</Text>
        <Text style={s.comingSoonTitle}>Notification settings are coming soon</Text>
      </View>

      <Text style={[gs.sectionTitle,{marginTop:8}]}>Privacy & Account</Text>
      <Card style={{ padding:0, overflow:"hidden" }}>
        {[
          { label:"Privacy Policy",       icon:"🔒", onPress: () => {} },
          { label:"Terms of Service",     icon:"📄", onPress: () => {} },
          { label:"Delete Account",       icon:"⚠️", onPress: () =>
            Alert.alert("Delete Account","This will permanently delete your account and all data. This cannot be undone.",[
              {text:"Cancel",style:"cancel"},
              {text:"Delete",style:"destructive",onPress:()=>{}},
            ])
          },
        ].map((row, i, arr) => (
          <TouchableOpacity key={row.label} style={[s.settingRow,
            i<arr.length-1&&{borderBottomWidth:1,borderBottomColor:theme.colors.border}]}
            onPress={row.onPress} activeOpacity={0.75}>
            <Text style={{ fontSize:18 }}>{row.icon}</Text>
            <Text style={[s.rowLabel,{flex:1}]}>{row.label}</Text>
            <Text style={{ fontSize:18, color:theme.colors.textTertiary }}>›</Text>
          </TouchableOpacity>
        ))}
      </Card>

      <Button label="Sign Out" variant="danger" size="md" fullWidth
        onPress={()=>Alert.alert("Sign Out","Are you sure?",[
          {text:"Cancel",style:"cancel"},
          {text:"Sign Out",style:"destructive",onPress:logout},
        ])}
      />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  settingRow:   { flexDirection:"row", alignItems:"center", gap:12, padding:14 },
  rowLabel:     { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  comingSoon:   { alignItems:"center", gap:8, padding:20, backgroundColor:theme.colors.surfaceSunken, borderRadius:theme.radius.lg },
  comingSoonTitle:{ fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary, textAlign:"center" },
});
