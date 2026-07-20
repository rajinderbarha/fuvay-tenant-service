import React, { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useApi, useAction } from "../hooks/useApi";
import { settingsApi, type CustomerSettings } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

const LANGUAGES = [
  { code:"en", label:"English" }, { code:"hi", label:"हिंदी" },
  { code:"mr", label:"मराठी" },  { code:"ta", label:"தமிழ்" },
  { code:"te", label:"తెలుగు" },
] as const;

export function SettingsScreen() {
  const navigation = useNavigation<any>();
  const { logout } = useAuth();
  const settings  = useApi(useCallback(() => settingsApi.get(), []));
  const saveAction = useAction(useCallback((s: Partial<CustomerSettings>) => settingsApi.update(s), []));

  const d = settings.data;
  const [notifs,  setNotifs]  = useState<CustomerSettings["notifications"] | null>(null);
  const [lang,    setLang]    = useState<string | null>(null);
  const [saved,   setSaved]   = useState(false);

  const N  = notifs ?? d?.notifications ?? { bookings:true, job_updates:true, promotions:false, sms:true, whatsapp:true };
  const L  = lang   ?? d?.language ?? "en";

  function toggle(key: keyof typeof N) {
    setNotifs({ ...N, [key]: !N[key] });
    setSaved(false);
  }

  async function handleSave() {
    const res = await saveAction.execute({ notifications: N, language: L as CustomerSettings["language"] });
    if (res) { setSaved(true); setTimeout(() => setSaved(false), 2500); settings.refetch(); }
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>

      {/* Notification preferences */}
      <Text style={gs.sectionTitle}>Notification Preferences</Text>
      <Card style={{ padding:0, overflow:"hidden" }}>
        {settings.loading ? <Skeleton height={200}/> : ([
          { key:"bookings",    label:"Booking updates",       sub:"Confirmation, reschedule, cancellation" },
          { key:"job_updates", label:"Job & technician alerts",sub:"En route, arrived, completed" },
          { key:"promotions",  label:"Offers & promotions",    sub:"Discounts and seasonal deals" },
          { key:"sms",         label:"SMS notifications",      sub:"Critical alerts via SMS" },
          { key:"whatsapp",    label:"WhatsApp messages",      sub:"Job updates on WhatsApp" },
        ] as const).map((row, i, arr) => (
          <View key={row.key} style={[s.settingRow, i<arr.length-1&&{borderBottomWidth:1,borderBottomColor:theme.colors.border}]}>
            <View style={{ flex:1 }}>
              <Text style={s.rowLabel}>{row.label}</Text>
              <Text style={s.rowSub}>{row.sub}</Text>
            </View>
            <Switch
              value={N[row.key]} onValueChange={() => toggle(row.key)}
              trackColor={{ true:theme.colors.accent, false:theme.colors.border }}
              thumbColor={theme.colors.surface}
            />
          </View>
        ))}
      </Card>

      {/* Language */}
      <Text style={[gs.sectionTitle,{marginTop:8}]}>Language</Text>
      <Card>
        <View style={{ flexDirection:"row", flexWrap:"wrap", gap:8 }}>
          {LANGUAGES.map(l => (
            <TouchableOpacity key={l.code} onPress={() => { setLang(l.code); setSaved(false); }} activeOpacity={0.8}
              style={[s.langChip, L===l.code && s.langChipActive]}>
              <Text style={[s.langText, L===l.code && s.langTextActive]}>{l.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </Card>

      {/* Privacy & account */}
      <Text style={[gs.sectionTitle,{marginTop:8}]}>Privacy & Account</Text>
      <Card style={{ padding:0, overflow:"hidden" }}>
        {[
          { label:"Privacy Policy",       icon:"🔒", onPress: () => {} },
          { label:"Terms of Service",     icon:"📄", onPress: () => {} },
          { label:"Data & Privacy",       icon:"🛡️", onPress: () => {} },
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

      {/* Save + sign out */}
      <Button
        label={saved ? "✓ Saved!" : saveAction.loading ? "Saving…" : "Save Settings"}
        variant={saved?"success":"primary"} size="lg" fullWidth
        loading={saveAction.loading} onPress={handleSave}
      />
      <Button label="Sign Out" variant="danger" size="md" fullWidth
        onPress={()=>Alert.alert("Sign Out","Are you sure?",[
          {text:"Cancel",style:"cancel"},
          {text:"Sign Out",style:"destructive",onPress:logout},
        ])}
      />

      {/* Development-only — never rendered in a production build (CUSTOMER-L5-00). */}
      {__DEV__ ? (
        <Button label="🧪 Design System Showcase (dev)" variant="secondary" size="md" fullWidth
          onPress={()=>navigation.navigate("DesignSystemShowcase")}
        />
      ) : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  settingRow:   { flexDirection:"row", alignItems:"center", gap:12, padding:14 },
  rowLabel:     { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  rowSub:       { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  langChip:     { paddingHorizontal:14, paddingVertical:8, borderRadius:theme.radius.full,
                  borderWidth:1, borderColor:theme.colors.border, backgroundColor:theme.colors.surfaceSunken },
  langChipActive:{ borderColor:theme.colors.brand, backgroundColor:theme.colors.brand },
  langText:     { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
  langTextActive:{ color:"#fff" },
});
