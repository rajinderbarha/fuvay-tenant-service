import React, { useCallback } from "react";
import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { paymentMethodsApi, type PaymentMethod } from "../lib/api";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

const TYPE_ICON: Record<string,string> = { upi:"🏦", card:"💳", netbanking:"🏛️", wallet:"👛" };
const TYPE_LABEL: Record<string,string>= { upi:"UPI",  card:"Card",  netbanking:"Net Banking", wallet:"Wallet" };

export function PaymentMethodsScreen() {
  const methods      = useApi(useCallback(() => paymentMethodsApi.list(), []));
  const setDefault   = useAction(useCallback((id:string) => paymentMethodsApi.setDefault(id), []));
  const removeAction = useAction(useCallback((id:string) => paymentMethodsApi.remove(id), []));

  async function handleSetDefault(id:string) {
    await setDefault.execute(id); methods.refetch();
  }

  async function handleRemove(id:string, name:string) {
    Alert.alert("Remove Payment Method",`Remove "${name}"?`,[
      {text:"Cancel",style:"cancel"},
      {text:"Remove",style:"destructive",onPress:async()=>{ await removeAction.execute(id); methods.refetch(); }},
    ]);
  }

  const list = methods.data?.methods ?? [];

  function renderMethod({ item:m }: { item:PaymentMethod }) {
    return (
      <Card style={{flexDirection:"row",alignItems:"center",gap:14}}>
        <View style={s.iconBox}>
          <Text style={{fontSize:24}}>{TYPE_ICON[m.type]??"💳"}</Text>
        </View>
        <View style={{flex:1}}>
          <View style={[gs.row,{gap:8}]}>
            <Text style={s.methodName}>{m.display_name}</Text>
            {m.is_default&&<View style={s.defaultBadge}><Text style={s.defaultText}>Default</Text></View>}
          </View>
          <Text style={s.methodSub}>{TYPE_LABEL[m.type]??"Payment method"}</Text>
          {m.last4&&<Text style={s.methodSub}>•••• {m.last4}</Text>}
          {m.upi_id&&<Text style={s.methodSub}>{m.upi_id}</Text>}
        </View>
        <View style={{gap:6}}>
          {!m.is_default&&(
            <TouchableOpacity onPress={()=>handleSetDefault(m.id)} style={s.actionBtn}>
              <Text style={s.actionText}>Set Default</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity onPress={()=>handleRemove(m.id,m.display_name)} style={[s.actionBtn,s.actionDanger]}>
            <Text style={[s.actionText,{color:theme.colors.dangerText}]}>Remove</Text>
          </TouchableOpacity>
        </View>
      </Card>
    );
  }

  return (
    <View style={gs.screen}>
      {methods.loading ? (
        <View style={{padding:16,gap:10}}>{[...Array(3)].map((_,i)=><Skeleton key={i} height={80}/>)}</View>
      ) : (
        <FlatList
          data={list}
          keyExtractor={m=>m.id}
          renderItem={renderMethod}
          contentContainerStyle={{padding:theme.spacing.base,gap:12,paddingBottom:40}}
          ListHeaderComponent={
            list.length > 0 ? (
              <View style={s.infoBox}>
                <Text style={s.infoText}>🔒 Your payment methods are secured with bank-grade encryption.</Text>
              </View>
            ) : null
          }
          ListEmptyComponent={
            <View style={{alignItems:"center",paddingVertical:60,gap:14}}>
              <Text style={{fontSize:44}}>💳</Text>
              <Text style={{fontSize:theme.font.size.lg,fontWeight:"700",color:theme.colors.textPrimary}}>
                No payment methods saved
              </Text>
              <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textSecondary,textAlign:"center",paddingHorizontal:32}}>
                Payment methods are added automatically when you complete a booking.
              </Text>
            </View>
          }
          onRefresh={methods.refetch}
          refreshing={methods.loading}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  iconBox:     { width:48, height:48, borderRadius:12, backgroundColor:theme.colors.surfaceSunken,
                 alignItems:"center", justifyContent:"center" },
  methodName:  { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  methodSub:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  defaultBadge:{ paddingHorizontal:7, paddingVertical:2, borderRadius:99, backgroundColor:theme.colors.successBg, borderWidth:1, borderColor:theme.colors.successBorder },
  defaultText: { fontSize:9, fontWeight:"700", color:theme.colors.successText },
  actionBtn:   { paddingHorizontal:10, paddingVertical:5, borderRadius:theme.radius.sm, borderWidth:1, borderColor:theme.colors.border },
  actionDanger:{ borderColor:theme.colors.dangerBorder, backgroundColor:theme.colors.dangerBg },
  actionText:  { fontSize:theme.font.size.xs, fontWeight:"600", color:theme.colors.textSecondary },
  infoBox:     { backgroundColor:theme.colors.successBg, borderRadius:theme.radius.md, padding:12,
                 borderWidth:1, borderColor:theme.colors.successBorder, marginBottom:12 },
  infoText:    { fontSize:theme.font.size.sm, color:theme.colors.successText },
});
