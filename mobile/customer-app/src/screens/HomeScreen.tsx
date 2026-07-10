import React, { useCallback } from "react";
import {
  ScrollView, StyleSheet, Text, TouchableOpacity,
  View, StatusBar, Dimensions,
} from "react-native";
import { useAuth }      from "../context/AuthContext";
import { useApi }       from "../hooks/useApi";
import { bookingsApi, jobsApi } from "../lib/api";
import { isActive }     from "../lib/jobStatus";
import { BookingCard }  from "../components/BookingCard";
import { Skeleton }     from "../components/Skeleton";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

const { width } = Dimensions.get("window");
const CARD_W = (width - 48) / 2;

// ── Category definitions ───────────────────────────────────────────────────────
const CATEGORIES = [
  { id:"ac",             icon:"❄️",  name:"AC & Cooling",     color:"#0EA5E9", bg:"#E0F2FE", types:["repair","service","consult"] },
  { id:"plumbing",       icon:"🔧",  name:"Plumbing",          color:"#3B82F6", bg:"#DBEAFE", types:["repair","service","consult"] },
  { id:"electrical",     icon:"⚡",  name:"Electrical",        color:"#F59E0B", bg:"#FEF3C7", types:["repair","service","consult"] },
  { id:"cleaning",       icon:"🧹",  name:"Cleaning",          color:"#10B981", bg:"#D1FAE5", types:["service"] },
  { id:"pest_control",   icon:"🪲",  name:"Pest Control",      color:"#8B5CF6", bg:"#EDE9FE", types:["service","consult"] },
  { id:"appliances",     icon:"🏠",  name:"Appliances",        color:"#6366F1", bg:"#E0E7FF", types:["repair","service"] },
  { id:"painting",       icon:"🎨",  name:"Painting",          color:"#EC4899", bg:"#FCE7F3", types:["service","consult"] },
  { id:"carpentry",      icon:"🪵",  name:"Carpentry",         color:"#D97706", bg:"#FEF3C7", types:["repair","service","consult"] },
  { id:"waterproofing",  icon:"💧",  name:"Waterproofing",     color:"#0284C7", bg:"#E0F2FE", types:["repair","service"] },
  { id:"interior_design",icon:"🏡",  name:"Interior Design",   color:"#14B8A6", bg:"#CCFBF1", types:["consult"] },
];

const TYPE_LABEL: Record<string,string> = {
  repair:"Repair", service:"Service", consult:"Consult",
};
const TYPE_COLOR: Record<string,string> = {
  repair:"#DC2626", service:"#16A34A", consult:"#7C3AED",
};

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// ── Component ──────────────────────────────────────────────────────────────────
type Props = NativeStackScreenProps<{ Home: undefined }, "Home">;

export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const recentBookings = useApi(useCallback(() =>
    bookingsApi.list({ limit: "3" }), []));
  const activeJob = useApi(useCallback(() =>
    jobsApi.list({ status: "active", limit: "1" }), []));

  function openCategory(catId: string) {
    navigation.navigate("SmartBot" as never, { categoryId: catId } as never);
  }

  const jobs = (activeJob.data as any)?.jobs ?? [];
  const hasActive = jobs.some((j: any) => isActive(j.status));

  return (
    <View style={s.screen}>
      <StatusBar barStyle="light-content" backgroundColor="#0F1F3A" />

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <View style={s.header}>
        <View>
          <Text style={s.greeting}>{greeting()}, {firstName} 👋</Text>
          <Text style={s.headerSub}>What do you need help with today?</Text>
        </View>
        <TouchableOpacity
          style={s.profileBtn}
          onPress={() => navigation.navigate("Profile" as never)}>
          <Text style={s.profileInitial}>{firstName[0]?.toUpperCase()}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={s.content}>

        {/* ── Active job banner ─────────────────────────────────────────────── */}
        {hasActive && (
          <TouchableOpacity
            style={s.activeBanner}
            onPress={() => navigation.navigate("JobTracking" as never,
              { jobId: jobs[0]?.id } as never)}
            activeOpacity={0.88}>
            <View style={s.activeDot}/>
            <View style={{ flex:1 }}>
              <Text style={s.activeBannerTitle}>Technician is on the way</Text>
              <Text style={s.activeBannerSub}>Tap to track live location</Text>
            </View>
            <Text style={s.activeBannerArrow}>›</Text>
          </TouchableOpacity>
        )}

        {/* ── Section: Services ────────────────────────────────────────────── */}
        <Text style={s.sectionLabel}>Services</Text>

        <View style={s.grid}>
          {CATEGORIES.map(cat => (
            <TouchableOpacity
              key={cat.id}
              style={[s.catCard, { backgroundColor: cat.bg }]}
              onPress={() => openCategory(cat.id)}
              activeOpacity={0.82}>

              {/* Color accent strip */}
              <View style={[s.catAccent, { backgroundColor: cat.color + "22",
                borderLeftColor: cat.color, borderLeftWidth: 3 }]}/>

              <Text style={s.catIcon}>{cat.icon}</Text>
              <Text style={[s.catName, { color: cat.color }]}>{cat.name}</Text>

              {/* Type pills */}
              <View style={s.typePills}>
                {cat.types.map(t => (
                  <View key={t}
                    style={[s.typePill, { backgroundColor: TYPE_COLOR[t] + "15",
                      borderColor: TYPE_COLOR[t] + "40" }]}>
                    <Text style={[s.typePillText, { color: TYPE_COLOR[t] }]}>
                      {TYPE_LABEL[t]}
                    </Text>
                  </View>
                ))}
              </View>

              {/* Tap cue */}
              <Text style={[s.tapCue, { color: cat.color + "99" }]}>Tap to start →</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Section: Recent Bookings ──────────────────────────────────────── */}
        <Text style={[s.sectionLabel, { marginTop: 28 }]}>Recent Bookings</Text>

        {recentBookings.loading
          ? [1,2].map(i => <Skeleton key={i} height={80} style={{ marginBottom:10, borderRadius:14 }}/>)
          : (recentBookings.data as any)?.bookings?.length === 0
          ? (
            <View style={s.emptyBookings}>
              <Text style={{ fontSize:32, marginBottom:8 }}>📋</Text>
              <Text style={s.emptyText}>No bookings yet</Text>
              <Text style={s.emptySubText}>Tap a category above to get started</Text>
            </View>
          )
          : (recentBookings.data as any)?.bookings?.slice(0,3).map((b: any) => (
            <BookingCard
              key={b.id} booking={b}
              onPress={() => navigation.navigate("BookingDetail" as never,
                { bookingId: b.id } as never)}
            />
          ))
        }

        <View style={{ height: 32 }}/>
      </ScrollView>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  screen:           { flex:1, backgroundColor:"#F5F7FA" },
  // Header
  header:           { backgroundColor:"#0F1F3A", paddingTop:56, paddingBottom:24,
                       paddingHorizontal:20, flexDirection:"row",
                       alignItems:"center", justifyContent:"space-between" },
  greeting:         { fontSize:22, fontWeight:"800", color:"#FFFFFF", letterSpacing:-0.3 },
  headerSub:        { fontSize:14, color:"rgba(255,255,255,0.6)", marginTop:3 },
  profileBtn:       { width:42, height:42, borderRadius:21,
                       backgroundColor:"rgba(255,255,255,0.15)",
                       alignItems:"center", justifyContent:"center" },
  profileInitial:   { fontSize:18, fontWeight:"700", color:"#FFFFFF" },
  // Content
  content:          { padding:16, paddingTop:20 },
  sectionLabel:     { fontSize:13, fontWeight:"700", color:"#94A3B8",
                       letterSpacing:0.8, textTransform:"uppercase", marginBottom:14 },
  // Active job banner
  activeBanner:     { flexDirection:"row", alignItems:"center", gap:12,
                       backgroundColor:"#0F1F3A", borderRadius:16, padding:16,
                       marginBottom:20, shadowColor:"#0F1F3A",
                       shadowOffset:{width:0,height:4}, shadowOpacity:0.25, shadowRadius:12,
                       elevation:6 },
  activeDot:        { width:10, height:10, borderRadius:5, backgroundColor:"#22C55E",
                       shadowColor:"#22C55E", shadowOffset:{width:0,height:0},
                       shadowOpacity:0.8, shadowRadius:4 },
  activeBannerTitle:{ fontSize:15, fontWeight:"700", color:"#FFFFFF" },
  activeBannerSub:  { fontSize:12, color:"rgba(255,255,255,0.6)", marginTop:2 },
  activeBannerArrow:{ fontSize:22, color:"rgba(255,255,255,0.5)" },
  // Category grid
  grid:             { flexDirection:"row", flexWrap:"wrap", gap:12 },
  catCard:          { width:CARD_W, borderRadius:18, padding:16, overflow:"hidden",
                       shadowColor:"#000", shadowOffset:{width:0,height:2},
                       shadowOpacity:0.08, shadowRadius:8, elevation:3,
                       position:"relative" },
  catAccent:        { position:"absolute", top:0, bottom:0, left:0, width:3,
                       borderTopLeftRadius:18, borderBottomLeftRadius:18 },
  catIcon:          { fontSize:34, marginBottom:10, marginTop:4 },
  catName:          { fontSize:15, fontWeight:"800", marginBottom:8, letterSpacing:-0.2 },
  typePills:        { flexDirection:"row", flexWrap:"wrap", gap:4, marginBottom:10 },
  typePill:         { paddingHorizontal:7, paddingVertical:3, borderRadius:6,
                       borderWidth:1 },
  typePillText:     { fontSize:10, fontWeight:"700", letterSpacing:0.3 },
  tapCue:           { fontSize:11, fontWeight:"600" },
  // Empty state
  emptyBookings:    { alignItems:"center", paddingVertical:32,
                       backgroundColor:"#FFFFFF", borderRadius:16, marginBottom:8 },
  emptyText:        { fontSize:15, fontWeight:"600", color:"#64748B" },
  emptySubText:     { fontSize:13, color:"#94A3B8", marginTop:4 },
});
