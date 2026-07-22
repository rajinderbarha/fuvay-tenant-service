import React, { useCallback } from "react";
import {
  ScrollView, StyleSheet, Text, TouchableOpacity, TextInput,
  View, Dimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth }      from "../context/AuthContext";
import { useTheme }     from "../context/ThemeContext";
import { useApi }       from "../hooks/useApi";
import { bookingsApi, fieldOpsJobsApi } from "../lib/api";
import { isActive }     from "../lib/jobStatus";
import { BookingCard }  from "../components/BookingCard";
import { Skeleton }     from "../components/Skeleton";
import type { Theme }   from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

const { width } = Dimensions.get("window");
const TILE_W = (width - 16 * 2 - 12 * 2) / 3;

// ── Popular-service tiles ────────────────────────────────────────────────────
// UX-07 Pass 3d: dropped the premature Repair/Service/Consult badges and the
// per-category pastel "hero card" treatment -- those choices belong INSIDE
// the guided SmartBot flow after category selection (see
// DeepSeekChatScreen.tsx), not on Home. Kept as compact single-icon tiles.
// `label` is passed to SmartBot as free-text context (matched against the
// real backend category list there) -- it is NOT assumed to equal a real
// backend category slug (Home's own tile list predates/doesn't track the
// backend catalog 1:1; see category-smartbot-handoff.md).
const POPULAR_SERVICES: { id:string; label:string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { id:"ac",           label:"AC Repair",   icon:"snow-outline" },
  { id:"plumbing",     label:"Plumbing",    icon:"water-outline" },
  { id:"electrical",   label:"Electrical",  icon:"flash-outline" },
  { id:"cleaning",     label:"Cleaning",    icon:"sparkles-outline" },
  { id:"appliances",   label:"Appliances",  icon:"hardware-chip-outline" },
  { id:"pest_control", label:"Pest Control",icon:"bug-outline" },
  { id:"more",         label:"More",        icon:"grid-outline" },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// ── Component ──────────────────────────────────────────────────────────────────
type Props = NativeStackScreenProps<{ Home: undefined }, "Home">;

// UX-07 Pass 3d: full information-architecture rebuild of Home. See
// docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/
// home-screen-root-cause-audit.md for the itemized "why it felt cluttered"
// findings this replaces (oversized hero banner, repeated "Home" title,
// generic "Customer" fallback greeting was never actually present but the
// greeting had no real-name path documented, emoji category icons,
// premature Repair/Service/Consult badges on Home, no search entry, no
// SmartBot primary CTA, wrapping 4-icon bottom nav).
export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const { theme } = useTheme();
  const s = makeStyles(theme);

  // Honest fallback: never fabricate a name. If AuthContext hasn't loaded a
  // real full_name yet, the greeting omits a name entirely rather than
  // showing a fake "Customer".
  const firstName = user?.full_name?.trim().split(/\s+/)[0] || null;
  const greetingText = firstName ? `${greeting()}, ${firstName}` : greeting();

  const [searchText, setSearchText] = React.useState("");

  const recentBookings = useApi(useCallback(() => bookingsApi.list(), []));
  const activeJob = useApi(useCallback(() => fieldOpsJobsApi.list(5), []));

  function goToSmartBot(initialCategoryLabel?: string) {
    (navigation.navigate as (...args: unknown[]) => void)("Tabs", {
      screen: "AIAssistant",
      params: initialCategoryLabel ? { initialCategoryLabel } : undefined,
    });
  }

  function submitSearch() {
    const q = searchText.trim();
    if (!q) { goToSmartBot(); return; }
    goToSmartBot(q);
  }

  const jobs = (activeJob.data as { jobs?: { job_id:string; status:string }[] } | null)?.jobs ?? [];
  const activeJobRecord = jobs.find(j => isActive(j.status)) ?? null;
  const bookingItems = (recentBookings.data as { items?: unknown[] } | null)?.items ?? [];

  return (
    <View style={s.screen}>
      {/* ── Top utility row ──────────────────────────────────────────────── */}
      <View style={s.topRow}>
        <TouchableOpacity style={s.locationChip} activeOpacity={0.75}
          onPress={() => navigation.navigate("AddressBook" as never)}
          accessible accessibilityRole="button" accessibilityLabel="Choose service location">
          <Ionicons name="location-outline" size={16} color={theme.colors.textInverse}/>
          <Text style={s.locationText} numberOfLines={1}>Choose service location</Text>
          <Ionicons name="chevron-down" size={14} color="rgba(255,255,255,0.7)"/>
        </TouchableOpacity>
        <View style={s.topIcons}>
          <TouchableOpacity style={s.iconBtn}
            onPress={() => (navigation.navigate as (...args: unknown[]) => void)("Tabs", { screen:"Notifications" })}
            accessible accessibilityRole="button" accessibilityLabel="Notifications">
            <Ionicons name="notifications-outline" size={20} color={theme.colors.textInverse}/>
          </TouchableOpacity>
          <TouchableOpacity style={s.avatarBtn}
            onPress={() => (navigation.navigate as (...args: unknown[]) => void)("Tabs", { screen:"Profile" })}
            accessible accessibilityRole="button" accessibilityLabel="Open profile"
            testID="home-profile-avatar">
            <Text style={s.avatarInitial}>{(firstName ?? "?")[0]?.toUpperCase()}</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.content}>
        {/* ── Greeting ──────────────────────────────────────────────────── */}
        <Text style={s.greeting} testID="home-greeting">{greetingText}</Text>
        <Text style={s.greetingSub}>What do you need help with today?</Text>

        {/* ── Search entry ──────────────────────────────────────────────── */}
        <View style={s.searchRow}>
          <Ionicons name="search-outline" size={18} color={theme.colors.textTertiary}/>
          <TextInput
            style={s.searchInput}
            value={searchText}
            onChangeText={setSearchText}
            onSubmitEditing={submitSearch}
            placeholder="Search AC repair, plumbing, cleaning…"
            placeholderTextColor={theme.colors.textTertiary}
            returnKeyType="search"
            testID="home-search-input"
            accessibilityLabel="Search for a service"
          />
        </View>

        {/* ── SmartBot CTA ──────────────────────────────────────────────── */}
        <TouchableOpacity style={s.smartbotCard} activeOpacity={0.9}
          onPress={() => goToSmartBot()} testID="home-smartbot-cta"
          accessible accessibilityRole="button" accessibilityLabel="Start with SmartBot">
          <View style={s.smartbotIconWrap}>
            <Ionicons name="sparkles" size={22} color={theme.colors.textInverse}/>
          </View>
          <View style={{ flex:1 }}>
            <Text style={s.smartbotTitle}>Smart Service Assistant</Text>
            <Text style={s.smartbotSub}>Describe your issue and get matched to the right service.</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={theme.colors.textInverse}/>
        </TouchableOpacity>

        {/* ── Active booking / empty state ──────────────────────────────── */}
        {activeJob.loading ? (
          <Skeleton height={72} style={{ marginTop:20, borderRadius:16 }}/>
        ) : activeJobRecord ? (
          <TouchableOpacity style={s.activeBanner} activeOpacity={0.88}
            onPress={() => (navigation.navigate as (...args: unknown[]) => void)("JobTracking", { jobId: activeJobRecord.job_id })}
            testID="home-active-booking"
            accessible accessibilityRole="button" accessibilityLabel="Track your active job">
            <View style={s.activeDot}/>
            <View style={{ flex:1 }}>
              <Text style={s.activeBannerTitle}>You have an active job</Text>
              <Text style={s.activeBannerSub}>Tap to track your job</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="rgba(255,255,255,0.7)"/>
          </TouchableOpacity>
        ) : (
          <View style={s.noActiveBanner} testID="home-no-active-booking">
            <Ionicons name="checkmark-circle-outline" size={18} color={theme.colors.textTertiary}/>
            <Text style={s.noActiveText}>No active jobs right now</Text>
          </View>
        )}

        {/* ── Popular services ──────────────────────────────────────────── */}
        <Text style={s.sectionLabel}>Popular services</Text>
        <View style={s.tileGrid}>
          {POPULAR_SERVICES.map(svc => (
            <TouchableOpacity
              key={svc.id}
              style={s.tile}
              onPress={() => svc.id === "more" ? goToSmartBot() : goToSmartBot(svc.label)}
              activeOpacity={0.8}
              accessible accessibilityRole="button" accessibilityLabel={svc.label}
              testID={`home-service-tile-${svc.id}`}>
              <View style={s.tileIconWrap}>
                <Ionicons name={svc.icon} size={22} color={theme.colors.brand}/>
              </View>
              <Text style={s.tileLabel} numberOfLines={1}>{svc.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Recent bookings ────────────────────────────────────────────── */}
        <Text style={[s.sectionLabel, { marginTop:24 }]}>Recent bookings</Text>
        {recentBookings.loading
          ? [1,2].map(i => <Skeleton key={i} height={80} style={{ marginBottom:10, borderRadius:14 }}/>)
          : bookingItems.length === 0 ? (
            <View style={s.emptyBookings} testID="home-no-bookings">
              <Ionicons name="document-text-outline" size={26} color={theme.colors.textTertiary}/>
              <Text style={s.emptyText}>No bookings yet</Text>
              <Text style={s.emptySubText}>Use SmartBot above to book your first service</Text>
            </View>
          ) : (bookingItems as any[]).slice(0,3).map((b: any) => (
            <BookingCard
              key={b.id} booking={b}
              onPress={() => (navigation.navigate as (...args: unknown[]) => void)("BookingDetail", { bookingId: b.id })}
            />
          ))
        }

        {/* ── Trust row ──────────────────────────────────────────────────── */}
        <View style={s.trustRow}>
          {[
            { icon:"shield-checkmark-outline" as const, label:"Verified pros" },
            { icon:"pricetag-outline" as const,          label:"Transparent pricing" },
            { icon:"cash-outline" as const,              label:"Pay on-site" },
            { icon:"help-buoy-outline" as const,         label:"Customer support" },
          ].map(t => (
            <View key={t.label} style={s.trustItem}>
              <Ionicons name={t.icon} size={16} color={theme.colors.textTertiary}/>
              <Text style={s.trustLabel} numberOfLines={2}>{t.label}</Text>
            </View>
          ))}
        </View>

        <View style={{ height:32 }}/>
      </ScrollView>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────
function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:           { flex:1, backgroundColor:theme.colors.bg },
    topRow:           { backgroundColor:theme.colors.brand, paddingTop:52, paddingBottom:14,
                        paddingHorizontal:16, flexDirection:"row", alignItems:"center", gap:10 },
    locationChip:     { flex:1, flexDirection:"row", alignItems:"center", gap:6,
                        backgroundColor:"rgba(255,255,255,0.14)", borderRadius:20,
                        paddingHorizontal:12, paddingVertical:8 },
    locationText:     { flex:1, fontSize:13, fontWeight:"600", color:theme.colors.textInverse },
    topIcons:         { flexDirection:"row", alignItems:"center", gap:8 },
    iconBtn:          { width:36, height:36, borderRadius:18, alignItems:"center", justifyContent:"center",
                        backgroundColor:"rgba(255,255,255,0.14)" },
    avatarBtn:        { width:36, height:36, borderRadius:18, alignItems:"center", justifyContent:"center",
                        backgroundColor:"rgba(255,255,255,0.22)" },
    avatarInitial:    { fontSize:15, fontWeight:"700", color:theme.colors.textInverse },
    content:          { padding:16, paddingTop:18 },
    greeting:         { fontSize:20, fontWeight:"800", color:theme.colors.textPrimary, letterSpacing:-0.3 },
    greetingSub:      { fontSize:13, color:theme.colors.textSecondary, marginTop:2, marginBottom:16 },
    searchRow:        { flexDirection:"row", alignItems:"center", gap:8,
                        backgroundColor:theme.colors.surface, borderRadius:14, borderWidth:1,
                        borderColor:theme.colors.border, paddingHorizontal:14, height:46, marginBottom:14 },
    searchInput:      { flex:1, fontSize:14, color:theme.colors.textPrimary, height:44 },
    smartbotCard:     { flexDirection:"row", alignItems:"center", gap:12,
                        backgroundColor:theme.colors.brand, borderRadius:16, padding:14,
                        marginBottom:14, ...theme.shadow.sm },
    smartbotIconWrap: { width:40, height:40, borderRadius:12, alignItems:"center", justifyContent:"center",
                        backgroundColor:"rgba(255,255,255,0.18)" },
    smartbotTitle:    { fontSize:14, fontWeight:"800", color:theme.colors.textInverse },
    smartbotSub:      { fontSize:11.5, color:"rgba(255,255,255,0.78)", marginTop:2 },
    activeBanner:     { flexDirection:"row", alignItems:"center", gap:12,
                        backgroundColor:theme.colors.brand, borderRadius:16, padding:14,
                        marginBottom:20, ...theme.shadow.sm },
    activeDot:        { width:9, height:9, borderRadius:5, backgroundColor:theme.colors.success },
    activeBannerTitle:{ fontSize:14, fontWeight:"700", color:theme.colors.textInverse },
    activeBannerSub:  { fontSize:11.5, color:"rgba(255,255,255,0.7)", marginTop:2 },
    noActiveBanner:   { flexDirection:"row", alignItems:"center", gap:8,
                        paddingVertical:12, paddingHorizontal:14, marginBottom:20,
                        backgroundColor:theme.colors.surfaceSunken, borderRadius:14 },
    noActiveText:     { fontSize:12.5, color:theme.colors.textTertiary, fontWeight:"600" },
    sectionLabel:     { fontSize:12.5, fontWeight:"700", color:theme.colors.textTertiary,
                        letterSpacing:0.6, textTransform:"uppercase", marginBottom:12 },
    tileGrid:         { flexDirection:"row", flexWrap:"wrap", gap:12, marginBottom:8 },
    tile:             { width:TILE_W, alignItems:"center", gap:6, backgroundColor:theme.colors.surface,
                        borderRadius:14, paddingVertical:14, ...theme.shadow.sm },
    tileIconWrap:     { width:40, height:40, borderRadius:12, alignItems:"center", justifyContent:"center",
                        backgroundColor:theme.colors.surfaceSunken },
    tileLabel:        { fontSize:11, fontWeight:"600", color:theme.colors.textSecondary, maxWidth:TILE_W-6 },
    emptyBookings:    { alignItems:"center", gap:4, paddingVertical:28,
                        backgroundColor:theme.colors.surface, borderRadius:16, marginBottom:8 },
    emptyText:        { fontSize:14, fontWeight:"600", color:theme.colors.textSecondary, marginTop:4 },
    emptySubText:     { fontSize:12, color:theme.colors.textTertiary },
    trustRow:         { flexDirection:"row", flexWrap:"wrap", gap:10, marginTop:24,
                        paddingTop:16, borderTopWidth:1, borderTopColor:theme.colors.border },
    trustItem:        { flexDirection:"row", alignItems:"center", gap:6, width:(width-16*2-10)/2 },
    trustLabel:       { fontSize:11, color:theme.colors.textTertiary, flexShrink:1 },
  });
}
