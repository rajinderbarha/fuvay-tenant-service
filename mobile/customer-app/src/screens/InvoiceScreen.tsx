import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { invoiceApi } from "../lib/api";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { invoiceId:string };
type RootParamList = { Invoice: Params };
type Props  = NativeStackScreenProps<RootParamList, "Invoice">;

/**
 * UX-06 Round 5 rewrite: trimmed to the real `ServiceInvoice` shape
 * (id/booking_id/job_id/status/amount/total/currency) — the prior version
 * read `invoice_number`/`issued_at`/`due_at`/`line_items`/`tax`/`pdf_url`,
 * none of which were ever confirmed real fields, and imported a type
 * (`Invoice`) that was never exported at all.
 *
 * UX-07 Pass 3b: confirmed `invoiceApi.get()` is real (GET
 * /v1/customer/service-invoices/{id}, src/lib/api.ts) -- this screen is
 * ACTIVE, not fixture data. Migrated off the static `theme`/`gs` import onto
 * useTheme().
 */
export function InvoiceScreen({ route }: Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const STATUS_STYLE: Record<string,{bg:string;text:string;border:string}> = {
    paid:    {bg:theme.colors.successBg, text:theme.colors.successText, border:theme.colors.successBorder},
    issued:  {bg:theme.colors.infoBg,    text:theme.colors.infoText,    border:theme.colors.infoBorder},
    overdue: {bg:theme.colors.dangerBg,  text:theme.colors.dangerText,  border:theme.colors.dangerBorder},
    draft:   {bg:theme.colors.surfaceSunken,text:theme.colors.textTertiary,border:theme.colors.border},
  };
  const { invoiceId } = route.params;
  const invoice = useApi(useCallback(() => invoiceApi.get(invoiceId), [invoiceId]));
  const inv = invoice.data;
  const fmt = (n?:number) => n != null ? `₹${n.toLocaleString("en-IN")}` : "—";
  const sc = STATUS_STYLE[inv?.status??"issued"] ?? STATUS_STYLE.issued;

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      {invoice.loading ? (
        <>{[...Array(3)].map((_,i)=><Skeleton key={i} height={90} style={{marginBottom:12}}/>)}</>
      ) : inv && (
        <Card>
          <View style={[s.row,{justifyContent:"space-between",marginBottom:14}]}>
            <Text style={s.invLabel}>SERVICE INVOICE</Text>
            <View style={[s.statusBadge,{backgroundColor:sc.bg,borderColor:sc.border}]}>
              <Text style={[s.statusText,{color:sc.text}]}>{inv.status.toUpperCase()}</Text>
            </View>
          </View>
          <View style={s.sep}/>
          <View style={[s.row,{justifyContent:"space-between",
            backgroundColor:theme.colors.surfaceSunken,borderRadius:theme.radius.md,
            padding:12,marginTop:14}]}>
            <Text style={{fontSize:theme.font.size.lg,fontWeight:"800",color:theme.colors.textPrimary}}>Total</Text>
            <Text style={{fontSize:theme.font.size.xl,fontWeight:"800",color:theme.colors.brand}}>
              {fmt(inv.total ?? inv.amount)} {inv.currency ?? ""}
            </Text>
          </View>
          <Text style={s.onSiteNote}>Paid directly to the technician on-site — ServiceOS does not process this payment.</Text>
        </Card>
      )}
    </ScrollView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:      { flex:1, backgroundColor:theme.colors.bg },
    row:         { flexDirection:"row", alignItems:"center" },
    sep:         { height:1, backgroundColor:theme.colors.border },
    content:     { padding:theme.spacing.base, gap:12, paddingBottom:40 },
    invLabel:    { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.textTertiary,
                   textTransform:"uppercase", letterSpacing:1 },
    statusBadge: { paddingHorizontal:12, paddingVertical:6, borderRadius:99, borderWidth:1 },
    statusText:  { fontSize:theme.font.size.xs, fontWeight:"800", letterSpacing:0.5 },
    onSiteNote:  { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:10, textAlign:"center" },
  });
}
