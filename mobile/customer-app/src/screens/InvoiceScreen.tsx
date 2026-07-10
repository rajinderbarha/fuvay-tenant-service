import React, { useCallback } from "react";
import { Linking, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { invoiceApi, type Invoice } from "../lib/api";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { invoiceId:string };
type Props  = NativeStackScreenProps<{ Invoice:Params }, "Invoice">;

const STATUS_STYLE: Record<string,{bg:string;text:string;border:string}> = {
  paid:    {bg:theme.colors.successBg, text:theme.colors.successText, border:theme.colors.successBorder},
  issued:  {bg:theme.colors.infoBg,    text:theme.colors.infoText,    border:theme.colors.infoBorder},
  overdue: {bg:theme.colors.dangerBg,  text:theme.colors.dangerText,  border:theme.colors.dangerBorder},
  draft:   {bg:theme.colors.surfaceSunken,text:theme.colors.textTertiary,border:theme.colors.border},
};

export function InvoiceScreen({ route }: Props) {
  const { invoiceId } = route.params;
  const invoice = useApi(useCallback(() => invoiceApi.get(invoiceId), [invoiceId]));
  const inv = invoice.data;
  const fmt = (n:number) => `₹${n.toLocaleString("en-IN")}`;
  const fmtDate = (d:string) => new Date(d).toLocaleDateString("en-IN",{day:"numeric",month:"long",year:"numeric"});
  const sc = STATUS_STYLE[inv?.status??"issued"];

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {invoice.loading ? (
        <>{[...Array(4)].map((_,i)=><Skeleton key={i} height={90} style={{marginBottom:12}}/>)}</>
      ) : inv && (
        <>
          {/* Invoice header */}
          <Card>
            <View style={[gs.row,{justifyContent:"space-between",marginBottom:14}]}>
              <View>
                <Text style={s.invLabel}>INVOICE</Text>
                <Text style={s.invNumber}>{inv.invoice_number}</Text>
              </View>
              <View style={[s.statusBadge,{backgroundColor:sc.bg,borderColor:sc.border}]}>
                <Text style={[s.statusText,{color:sc.text}]}>{inv.status.toUpperCase()}</Text>
              </View>
            </View>
            <View style={gs.sep}/>
            <View style={[gs.row,{justifyContent:"space-between",marginTop:12}]}>
              <View>
                <Text style={s.metaLabel}>Issued</Text>
                <Text style={s.metaVal}>{fmtDate(inv.issued_at)}</Text>
              </View>
              {inv.due_at&&(
                <View style={{alignItems:"flex-end"}}>
                  <Text style={s.metaLabel}>Due</Text>
                  <Text style={s.metaVal}>{fmtDate(inv.due_at)}</Text>
                </View>
              )}
            </View>
          </Card>

          {/* Line items */}
          <Card>
            <Text style={[gs.label,{marginBottom:14}]}>Service Breakdown</Text>
            {inv.line_items.map((li,i)=>(
              <View key={i} style={[gs.row,{justifyContent:"space-between",
                paddingBottom:i<inv.line_items.length-1?10:0,
                marginBottom:i<inv.line_items.length-1?10:0,
                borderBottomWidth:i<inv.line_items.length-1?1:0,
                borderBottomColor:theme.colors.border}]}>
                <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textSecondary,flex:1,paddingRight:10}}>
                  {li.description}
                </Text>
                <Text style={{fontSize:theme.font.size.sm,fontWeight:"600",color:theme.colors.textPrimary}}>
                  {fmt(li.amount)}
                </Text>
              </View>
            ))}
            <View style={[gs.sep,{marginTop:14,marginBottom:12}]}/>
            {[
              {label:"Subtotal",  val:fmt(inv.amount)},
              {label:"GST (18%)", val:fmt(inv.tax)},
            ].map(row=>(
              <View key={row.label} style={[gs.row,{justifyContent:"space-between",marginBottom:6}]}>
                <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textSecondary}}>{row.label}</Text>
                <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textPrimary,fontWeight:"600"}}>{row.val}</Text>
              </View>
            ))}
            <View style={[gs.row,{justifyContent:"space-between",
              backgroundColor:theme.colors.surfaceSunken,borderRadius:theme.radius.md,
              padding:12,marginTop:8}]}>
              <Text style={{fontSize:theme.font.size.lg,fontWeight:"800",color:theme.colors.textPrimary}}>Total</Text>
              <Text style={{fontSize:theme.font.size.xl,fontWeight:"800",color:theme.colors.brand}}>{fmt(inv.total)}</Text>
            </View>
          </Card>

          {/* Download */}
          {inv.pdf_url && (
            <TouchableOpacity style={s.downloadBtn}
              onPress={()=>Linking.openURL(inv.pdf_url!)} activeOpacity={0.85}>
              <Text style={s.downloadText}>⬇ Download PDF Invoice</Text>
            </TouchableOpacity>
          )}
        </>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:     { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  invLabel:    { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.textTertiary,
                 textTransform:"uppercase", letterSpacing:1 },
  invNumber:   { fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.brand, marginTop:3 },
  statusBadge: { paddingHorizontal:12, paddingVertical:6, borderRadius:99, borderWidth:1 },
  statusText:  { fontSize:theme.font.size.xs, fontWeight:"800", letterSpacing:0.5 },
  metaLabel:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary,
                 textTransform:"uppercase", letterSpacing:0.5 },
  metaVal:     { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary, marginTop:2 },
  downloadBtn: { backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg, padding:16,
                 alignItems:"center", ...theme.shadow.md },
  downloadText:{ fontSize:theme.font.size.base, fontWeight:"700", color:"#fff" },
});
