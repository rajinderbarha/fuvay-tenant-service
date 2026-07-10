import React, { useCallback, useState } from "react";
import { Alert, KeyboardAvoidingView, Modal, Platform, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { addressApi, type SavedAddress } from "../lib/api";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";

const LABEL_ICONS: Record<string,string> = { home:"🏠", work:"💼", other:"📍" };

const EMPTY_FORM = { label:"home" as SavedAddress["label"], address_line:"", city:"", pincode:"" };

export function AddressBookScreen() {
  const addresses    = useApi(useCallback(() => addressApi.list(), []));
  const addAction    = useAction(useCallback((a:Parameters<typeof addressApi.add>[0]) => addressApi.add(a), []));
  const deleteAction = useAction(useCallback((id:string) => addressApi.delete(id), []));
  const defaultAction= useAction(useCallback((id:string) => addressApi.setDefault(id), []));

  const [modal, setModal] = useState(false);
  const [form,  setForm]  = useState(EMPTY_FORM);

  async function handleAdd() {
    if (!form.address_line.trim() || !form.city.trim()) {
      Alert.alert("Missing fields","Please fill address and city."); return;
    }
    const res = await addAction.execute(form);
    if (res) { setModal(false); setForm(EMPTY_FORM); addresses.refetch(); }
  }

  async function handleDelete(id:string) {
    Alert.alert("Remove Address","Remove this saved address?",[
      {text:"Cancel",style:"cancel"},
      {text:"Remove",style:"destructive",onPress:async()=>{ await deleteAction.execute(id); addresses.refetch(); }},
    ]);
  }

  async function handleSetDefault(id:string) {
    await defaultAction.execute(id); addresses.refetch();
  }

  const list = addresses.data?.addresses ?? [];

  return (
    <View style={gs.screen}>
      <ScrollView contentContainerStyle={s.content}>
        {addresses.loading ? (
          <>{[...Array(3)].map((_,i)=><Skeleton key={i} height={90}/>)}</>
        ) : list.length === 0 ? (
          <View style={[gs.card,{alignItems:"center",paddingVertical:40,gap:12}]}>
            <Text style={{fontSize:36}}>📍</Text>
            <Text style={{fontSize:theme.font.size.lg,fontWeight:"700",color:theme.colors.textPrimary}}>No saved addresses</Text>
            <Text style={{fontSize:theme.font.size.sm,color:theme.colors.textSecondary,textAlign:"center"}}>
              Save your home, work, and other addresses for faster booking.
            </Text>
          </View>
        ) : list.map(addr => (
          <Card key={addr.id} style={{gap:10}}>
            <View style={gs.row}>
              <Text style={{fontSize:22,marginRight:10}}>{LABEL_ICONS[addr.label]??"📍"}</Text>
              <View style={{flex:1}}>
                <View style={[gs.row,{gap:8}]}>
                  <Text style={s.addrLabel}>{addr.label.charAt(0).toUpperCase()+addr.label.slice(1)}</Text>
                  {addr.is_default && (
                    <View style={s.defaultBadge}><Text style={s.defaultText}>Default</Text></View>
                  )}
                </View>
                <Text style={s.addrLine}>{addr.address_line}</Text>
                <Text style={s.addrCity}>{addr.city}{addr.pincode?` - ${addr.pincode}`:""}</Text>
              </View>
            </View>
            <View style={[gs.row,{gap:10,justifyContent:"flex-end"}]}>
              {!addr.is_default && (
                <TouchableOpacity onPress={()=>handleSetDefault(addr.id)}
                  style={s.actionBtn} disabled={defaultAction.loading}>
                  <Text style={s.actionBtnText}>Set Default</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={()=>handleDelete(addr.id)} style={[s.actionBtn,s.actionBtnDanger]}>
                <Text style={[s.actionBtnText,{color:theme.colors.dangerText}]}>Remove</Text>
              </TouchableOpacity>
            </View>
          </Card>
        ))}

        <Button label="+ Add New Address" variant="outline" size="lg" fullWidth onPress={()=>setModal(true)}/>
      </ScrollView>

      {/* Add address modal */}
      <Modal visible={modal} transparent animationType="slide" onRequestClose={()=>setModal(false)}>
        <KeyboardAvoidingView style={s.overlay} behavior={Platform.OS==="ios"?"padding":"height"}>
          <ScrollView style={s.sheet} contentContainerStyle={{gap:14,paddingBottom:40}}>
            <Text style={s.modalTitle}>Add Address</Text>

            <View>
              <Text style={s.fieldLabel}>Label</Text>
              <View style={{flexDirection:"row",gap:8}}>
                {(["home","work","other"] as const).map(l=>(
                  <TouchableOpacity key={l} onPress={()=>setForm(p=>({...p,label:l}))}
                    style={[s.labelChip, form.label===l&&s.labelChipActive]}>
                    <Text style={[s.labelChipText,form.label===l&&{color:"#fff"}]}>
                      {LABEL_ICONS[l]} {l.charAt(0).toUpperCase()+l.slice(1)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {[
              {key:"address_line",label:"Street Address *",    placeholder:"Flat 12B, Sunrise Apartments, MG Road"},
              {key:"city",        label:"City *",              placeholder:"Mumbai"},
              {key:"pincode",     label:"Pincode",             placeholder:"400001"},
            ].map(f=>(
              <View key={f.key}>
                <Text style={s.fieldLabel}>{f.label}</Text>
                <TextInput style={s.input} value={(form as Record<string,string>)[f.key]}
                  onChangeText={v=>setForm(p=>({...p,[f.key]:v}))}
                  placeholder={f.placeholder} placeholderTextColor={theme.colors.textTertiary}/>
              </View>
            ))}

            {addAction.error && <Text style={{color:theme.colors.dangerText,fontSize:theme.font.size.sm}}>{addAction.error}</Text>}
            <Button label="Save Address" variant="primary" size="lg" loading={addAction.loading} onPress={handleAdd} fullWidth/>
            <Button label="Cancel" variant="ghost" size="md" onPress={()=>{setModal(false);setForm(EMPTY_FORM);}} fullWidth/>
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  content:       { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  addrLabel:     { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  addrLine:      { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  addrCity:      { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  defaultBadge:  { paddingHorizontal:8, paddingVertical:2, borderRadius:99,
                   backgroundColor:theme.colors.successBg, borderWidth:1, borderColor:theme.colors.successBorder },
  defaultText:   { fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.successText },
  actionBtn:     { paddingHorizontal:12, paddingVertical:7, borderRadius:theme.radius.md,
                   borderWidth:1, borderColor:theme.colors.border },
  actionBtnDanger:{ borderColor:theme.colors.dangerBorder, backgroundColor:theme.colors.dangerBg },
  actionBtnText: { fontSize:theme.font.size.xs, fontWeight:"600", color:theme.colors.textSecondary },
  overlay:       { flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.4)" },
  sheet:         { backgroundColor:theme.colors.surface, borderTopLeftRadius:28,
                   borderTopRightRadius:28, padding:24, maxHeight:"90%" },
  modalTitle:    { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  fieldLabel:    { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary, marginBottom:6 },
  input:         { height:46, borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                   paddingHorizontal:14, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                   backgroundColor:theme.colors.surfaceSunken },
  labelChip:     { flex:1, paddingVertical:9, borderRadius:theme.radius.md, borderWidth:1,
                   borderColor:theme.colors.border, alignItems:"center" },
  labelChipActive:{ borderColor:theme.colors.brand, backgroundColor:theme.colors.brand },
  labelChipText: { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
});
