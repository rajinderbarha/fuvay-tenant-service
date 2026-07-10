import React, { useCallback, useState } from "react";
import { Alert, Linking, Modal, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { helpApi, type FaqItem } from "../lib/api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

const CONTACT_OPTIONS = [
  { icon:"📞", label:"Call Support",   sub:"Mon–Sat, 8 AM – 10 PM", onPress:()=>Linking.openURL("tel:1800XXXXXXX") },
  { icon:"✉️", label:"Email Us",       sub:"Response within 24h",    onPress:()=>Linking.openURL("mailto:support@serviceos.com") },
  { icon:"💬", label:"WhatsApp",        sub:"Quick replies",           onPress:()=>Linking.openURL("https://wa.me/91XXXXXXXXXX") },
];

export function HelpSupportScreen() {
  const faqs       = useApi(useCallback(() => helpApi.faqs(), []));
  const [expanded, setExpanded] = useState<string|null>(null);
  const [modal,    setModal]    = useState(false);
  const [subject,  setSubject]  = useState("");
  const [message,  setMessage]  = useState("");
  const [sent,     setSent]     = useState(false);

  const ticketAction = useAction(useCallback(
    (sub:string, msg:string) => helpApi.submitTicket(sub, msg), []
  ));

  async function handleSubmit() {
    if (!subject.trim()||!message.trim()) { Alert.alert("Required","Please fill all fields."); return; }
    const res = await ticketAction.execute(subject.trim(), message.trim());
    if (res) { setSent(true); setSubject(""); setMessage(""); }
  }

  const allFaqs = faqs.data?.faqs ?? [];

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>

      {/* Contact options */}
      <Text style={gs.sectionTitle}>Contact Us</Text>
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

      {/* Raise a ticket */}
      <TouchableOpacity style={s.ticketBanner} onPress={()=>setModal(true)} activeOpacity={0.85}>
        <View>
          <Text style={s.ticketTitle}>🎫 Raise a Support Ticket</Text>
          <Text style={s.ticketSub}>Issue with a booking or service? Let us know.</Text>
        </View>
        <Text style={{fontSize:20,color:"#fff"}}>→</Text>
      </TouchableOpacity>

      {/* FAQs */}
      <Text style={[gs.sectionTitle,{marginTop:4}]}>Frequently Asked Questions</Text>
      {faqs.loading ? (
        <>{[...Array(4)].map((_,i)=><Skeleton key={i} height={52} style={{marginBottom:8}}/>)}</>
      ) : allFaqs.length === 0 ? (
        <Text style={{color:theme.colors.textTertiary,fontSize:theme.font.size.base,textAlign:"center",padding:24}}>
          FAQs loading…
        </Text>
      ) : allFaqs.map((faq,i)=>(
        <TouchableOpacity key={i} onPress={()=>setExpanded(expanded===`faq${i}`?null:`faq${i}`)}
          activeOpacity={0.8} style={s.faqItem}>
          <View style={[gs.row,{justifyContent:"space-between"}]}>
            <Text style={[s.faqQ,{flex:1,paddingRight:10}]}>{faq.question}</Text>
            <Text style={{fontSize:18,color:theme.colors.textTertiary}}>
              {expanded===`faq${i}` ? "▲" : "▼"}
            </Text>
          </View>
          {expanded===`faq${i}` && (
            <Text style={s.faqA}>{faq.answer}</Text>
          )}
        </TouchableOpacity>
      ))}

      {/* Ticket Modal */}
      <Modal visible={modal} transparent animationType="slide" onRequestClose={()=>setModal(false)}>
        <View style={s.overlay}>
          <View style={s.sheet}>
            {sent ? (
              <View style={{alignItems:"center",gap:16,paddingVertical:20}}>
                <Text style={{fontSize:48}}>✅</Text>
                <Text style={{fontSize:theme.font.size.xl,fontWeight:"700",color:theme.colors.textPrimary}}>Ticket Submitted!</Text>
                <Text style={{fontSize:theme.font.size.base,color:theme.colors.textSecondary,textAlign:"center"}}>
                  We'll get back to you within 24 hours.
                </Text>
                <Button label="Done" variant="primary" size="lg" fullWidth onPress={()=>{setModal(false);setSent(false);}}/>
              </View>
            ) : (
              <>
                <Text style={s.modalTitle}>Raise a Ticket</Text>
                <View>
                  <Text style={s.fieldLabel}>Subject *</Text>
                  <TextInput style={s.input} value={subject} onChangeText={setSubject}
                    placeholder="e.g. Technician didn't arrive on time"
                    placeholderTextColor={theme.colors.textTertiary}/>
                </View>
                <View>
                  <Text style={s.fieldLabel}>Describe the issue *</Text>
                  <TextInput style={[s.input,{height:100,paddingTop:10,textAlignVertical:"top"}]}
                    value={message} onChangeText={setMessage} multiline
                    placeholder="Please provide as much detail as possible…"
                    placeholderTextColor={theme.colors.textTertiary}/>
                </View>
                {ticketAction.error&&<Text style={{color:theme.colors.dangerText,fontSize:theme.font.size.sm}}>{ticketAction.error}</Text>}
                <Button label="Submit Ticket" variant="primary" size="lg" fullWidth
                  loading={ticketAction.loading} onPress={handleSubmit}/>
                <Button label="Cancel" variant="ghost" size="md" fullWidth onPress={()=>setModal(false)}/>
              </>
            )}
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:14, paddingBottom:40 },
  contactRow:   { flexDirection:"row", alignItems:"center", padding:14 },
  contactLabel: { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  contactSub:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  ticketBanner: { flexDirection:"row", alignItems:"center", justifyContent:"space-between",
                  backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg, padding:16,
                  ...theme.shadow.md },
  ticketTitle:  { fontSize:theme.font.size.lg, fontWeight:"700", color:"#fff", marginBottom:4 },
  ticketSub:    { fontSize:theme.font.size.sm, color:"rgba(255,255,255,0.75)" },
  faqItem:      { backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
                  padding:14, ...theme.shadow.sm, gap:8 },
  faqQ:         { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  faqA:         { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, lineHeight:22 },
  overlay:      { flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.4)" },
  sheet:        { backgroundColor:theme.colors.surface, borderTopLeftRadius:28,
                  borderTopRightRadius:28, padding:24, gap:14, paddingBottom:40 },
  modalTitle:   { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  fieldLabel:   { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary, marginBottom:6 },
  input:        { height:46, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                  paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                  backgroundColor:theme.colors.surfaceSunken },
});
