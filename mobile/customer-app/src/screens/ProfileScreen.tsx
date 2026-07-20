import React, { useCallback } from "react";
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { profileApi } from "../lib/api";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Props = NativeStackScreenProps<{ Profile:undefined }, "Profile">;

export function ProfileScreen({ navigation }: Props) {
  const { user, logout } = useAuth();
  const profile = useApi(useCallback(() => profileApi.get(), []));
  const p = profile.data;
  const fmt = (n:number) => `₹${n.toLocaleString("en-IN")}`;

  const SECTIONS = [
    {
      title: "My Account",
      items: [
        { icon:"📋", label:"My Bookings",      onPress:() => navigation.navigate("Bookings" as never) },
        { icon:"🔧", label:"Service History",  onPress:() => navigation.navigate("ServiceHistory" as never) },
        { icon:"📍", label:"Saved Addresses",  onPress:() => navigation.navigate("AddressBook"    as never) },
        { icon:"💳", label:"Payment Methods",  onPress:() => navigation.navigate("PaymentMethods" as never) },
      ],
    },
    {
      title: "Preferences",
      items: [
        { icon:"🔔", label:"Notifications",    onPress:() => navigation.navigate("Notifications"  as never) },
        { icon:"⚙️", label:"Settings",         onPress:() => navigation.navigate("Settings"       as never) },
      ],
    },
    {
      title: "Support",
      items: [
        { icon:"❓", label:"Help & Support",   onPress:() => navigation.navigate("HelpSupport"    as never) },
        { icon:"🤖", label:"AI Assistant",     onPress:() => navigation.navigate("AIAssistant"    as never) },
      ],
    },
  ];

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {/* Profile header */}
      {profile.loading ? <Skeleton height={90}/> : (
        <Card style={{ flexDirection:"row", alignItems:"center", gap:14 }}>
          <View style={s.avatar}>
            <Text style={s.avatarText}>{(p?.full_name??user?.full_name??"?")[0]?.toUpperCase()}</Text>
          </View>
          <View style={{ flex:1 }}>
            <Text style={s.name}>{p?.full_name ?? user?.full_name ?? "—"}</Text>
            {p?.phone&&<Text style={s.sub}>{p.phone}</Text>}
            {p?.email&&<Text style={s.sub}>{p.email}</Text>}
          </View>
          <TouchableOpacity onPress={()=>navigation.navigate("Settings" as never)}
            style={s.editBtn} activeOpacity={0.75}>
            <Text style={s.editText}>Edit ✎</Text>
          </TouchableOpacity>
        </Card>
      )}

      {/* UX-06 Round 5: removed a "stats" row (total_jobs/health_score/
          health_band) that read fields never confirmed to exist on the real
          CustomerUser/profile response, AND would have exposed internal
          health/ranking scores to the customer -- a hard-forbidden item per
          the canonical domain rules ("never expose internal ranking/health
          scores"). This was a real rule violation fixed this round, not
          just a typecheck cleanup. */}

      {/* Sectioned menu */}
      {SECTIONS.map(section => (
        <View key={section.title}>
          <Text style={[gs.label,{marginBottom:8}]}>{section.title}</Text>
          <Card style={{ padding:0, overflow:"hidden" }}>
            {section.items.map((item, i, arr) => (
              <TouchableOpacity key={item.label}
                style={[s.menuItem, i<arr.length-1&&{borderBottomWidth:1,borderBottomColor:theme.colors.border}]}
                onPress={item.onPress} activeOpacity={0.75}>
                <Text style={{ fontSize:20 }}>{item.icon}</Text>
                <Text style={s.menuLabel}>{item.label}</Text>
                <Text style={s.menuArrow}>›</Text>
              </TouchableOpacity>
            ))}
          </Card>
        </View>
      ))}

      {/* Sign out */}
      <TouchableOpacity style={s.logoutBtn} activeOpacity={0.8}
        onPress={()=>Alert.alert("Sign Out","Are you sure?",[
          {text:"Cancel",style:"cancel"},
          {text:"Sign Out",style:"destructive",onPress:logout}
        ])}>
        <Text style={s.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <Text style={{textAlign:"center",fontSize:theme.font.size.xs,
        color:theme.colors.textTertiary}}>ServiceOS v1.0.0</Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:   { padding:theme.spacing.base, gap:14, paddingBottom:40 },
  avatar:    { width:60, height:60, borderRadius:30, backgroundColor:theme.colors.brand,
               alignItems:"center", justifyContent:"center" },
  avatarText:{ fontSize:theme.font.size.xxl, fontWeight:"800", color:"#fff" },
  name:      { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  sub:       { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:2 },
  editBtn:   { paddingHorizontal:10, paddingVertical:5, borderRadius:theme.radius.sm,
               borderWidth:1, borderColor:theme.colors.border },
  editText:  { fontSize:theme.font.size.xs, fontWeight:"600", color:theme.colors.textSecondary },
  statsRow:  { flexDirection:"row", gap:10 },
  statBox:   { flex:1, backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
               padding:14, alignItems:"center", gap:4, ...theme.shadow.sm },
  statVal:   { fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.textPrimary },
  statLabel: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, fontWeight:"600",
               textTransform:"uppercase", letterSpacing:0.5 },
  menuItem:  { flexDirection:"row", alignItems:"center", gap:14, padding:16 },
  menuLabel: { flex:1, fontSize:theme.font.size.base, fontWeight:"500", color:theme.colors.textPrimary },
  menuArrow: { fontSize:theme.font.size.xl, color:theme.colors.textTertiary },
  logoutBtn: { alignItems:"center", padding:16, backgroundColor:theme.colors.dangerBg,
               borderRadius:theme.radius.lg, borderWidth:1, borderColor:theme.colors.dangerBorder },
  logoutText:{ fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.dangerText },
});
