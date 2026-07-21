import React from "react";
import { Linking, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Card } from "../components/Card";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";

const CONTACT_OPTIONS = [
  { icon:"📞", label:"Call Support",   sub:"Mon–Sat, 8 AM – 10 PM", onPress:()=>Linking.openURL("tel:1800XXXXXXX") },
  { icon:"✉️", label:"Email Us",       sub:"Response within 24h",    onPress:()=>Linking.openURL("mailto:support@serviceos.com") },
  { icon:"💬", label:"WhatsApp",        sub:"Quick replies",           onPress:()=>Linking.openURL("https://wa.me/91XXXXXXXXXX") },
];

/**
 * UX-06 ROUND 2: no real backend contract for /v1/help/faqs or a ticket-submission
 * endpoint was found anywhere in the live openapi.json this round. The static
 * contact-options card (phone/email/WhatsApp deep links) needs no backend and is
 * kept as-is; the FAQ list and "raise a ticket" form (which previously called
 * nonexistent helpApi.faqs()/submitTicket()) were converted to an honest
 * "coming soon" note rather than left calling guessed endpoints. Note: the
 * backend DOES have a real /v1/customer/complaints* engine — that may be the
 * intended production home for "raise an issue" in a future round, but it models
 * a structured complaint/settlement workflow, not a free-text support ticket, so
 * it wasn't reused here without confirming that's the right fit.
 *
 * UX-07 Pass 3b: migrated off the static `theme`/`gs` import onto useTheme().
 */
export function HelpSupportScreen() {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      <Text style={s.sectionTitle}>Contact Us</Text>
      <Card style={{padding:0,overflow:"hidden"}}>
        {CONTACT_OPTIONS.map((opt,i,arr)=>(
          <TouchableOpacity key={opt.label} style={[s.contactRow,
            i<arr.length-1&&{borderBottomWidth:1,borderBottomColor:theme.colors.border}]}
            onPress={opt.onPress} activeOpacity={0.75}>
            <Text style={{fontSize:26,marginRight:12}}>{opt.icon}</Text>
            <View style={{flex:1}}>
              <Text style={s.contactLabel}>{opt.label}</Text>
              <Text style={s.contactSub}>{opt.sub}</Text>
            </View>
            <Text style={{fontSize:18,color:theme.colors.textTertiary}}>›</Text>
          </TouchableOpacity>
        ))}
      </Card>

      <View style={s.comingSoon}>
        <Text style={{fontSize:32}}>🚧</Text>
        <Text style={s.comingSoonTitle}>FAQs & support tickets are coming soon</Text>
        <Text style={s.comingSoonBody}>
          For now, please reach us using one of the contact options above.
        </Text>
      </View>
    </ScrollView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:       { flex:1, backgroundColor:theme.colors.bg },
    sectionTitle: { fontSize:theme.font.size.lg, fontWeight:theme.font.weight.bold, color:theme.colors.textPrimary },
    content:      { padding:theme.spacing.base, gap:14, paddingBottom:40 },
    contactRow:   { flexDirection:"row", alignItems:"center", padding:14 },
    contactLabel: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
    contactSub:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
    comingSoon:   { alignItems:"center", gap:8, padding:28 },
    comingSoonTitle:{ fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
    comingSoonBody: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center" },
  });
}
