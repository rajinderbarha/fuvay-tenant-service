import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { catalogApi } from "../lib/api";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { categorySlug: string; offeringSlug: string };
type RootParamList = { ServiceDetail: Params };
type Props = NativeStackScreenProps<RootParamList, "ServiceDetail">;

/**
 * UX-06 Round 5 — new standalone Service Detail screen (Workstream 7), the
 * previously-unverified/nonexistent 3rd screen from Round 4's audit. Real
 * data only: GET /v1/customer/categories/{category_slug}/offerings/{offering_slug}
 * (app/engines/customer_flow/router.py::get_customer_offering, confirmed
 * real this round while fixing the booking-draft required-fields contract).
 * No fixture data, no internal readiness labels, no raw API field dumps —
 * every value below is a named, human-labeled real field.
 *
 * UX-07 Pass 3b: migrated off the static `theme`/`gs` import onto useTheme().
 */
export function ServiceDetailScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const { categorySlug, offeringSlug } = route.params;
  const offering = useApi(useCallback(
    () => catalogApi.offeringDetail(categorySlug, offeringSlug), [categorySlug, offeringSlug]
  ));
  const o = offering.data;

  if (offering.loading) {
    return (
      <ScrollView style={s.screen} contentContainerStyle={{ padding:theme.spacing.base, gap:14 }}>
        <Skeleton height={140}/>
        <Skeleton height={80}/>
      </ScrollView>
    );
  }

  if (offering.error || !o) {
    return (
      <View style={[s.screen, s.center]}>
        <Text style={s.icon}>⚠️</Text>
        <Text style={s.title}>Couldn't load this service</Text>
        <Text style={s.body}>Please check your connection and try again.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      <Card style={{ gap:8 }}>
        <Text style={s.name}>{o.name}</Text>
        <Text style={s.category}>{o.category?.name}</Text>
        {o.description && <Text style={s.description}>{o.description}</Text>}
      </Card>

      <Card style={{ gap:8 }}>
        <Text style={s.label}>Price</Text>
        {o.starting_price != null ? (
          <Text style={s.price}>Starting from ₹{o.starting_price.toLocaleString("en-IN")}</Text>
        ) : (
          <Text style={s.body}>Price shown after checking your area</Text>
        )}
        {!!o.visit_fee && o.visit_fee > 0 && (
          <Text style={s.footnote}>Includes a ₹{o.visit_fee} visit fee</Text>
        )}
      </Card>

      <Card style={{ gap:8 }}>
        <Text style={s.label}>What we need from you</Text>
        {o.requires_brand    && <Text style={s.body}>• Appliance brand</Text>}
        {o.requires_type     && <Text style={s.body}>• Service type</Text>}
        {o.requires_address  && <Text style={s.body}>• Your address</Text>}
        {o.requires_slot     && <Text style={s.body}>• A preferred time slot</Text>}
        {!o.requires_brand && !o.requires_type && !o.requires_address && !o.requires_slot && (
          <Text style={s.body}>Just a quick description of the issue</Text>
        )}
      </Card>

      <Text style={s.onSiteNote}>You pay the technician on-site — ServiceOS does not process this payment.</Text>

      <TouchableOpacity style={s.bookBtn} onPress={()=>(navigation.navigate as (...args: unknown[]) => void)("Tabs", { screen:"AIAssistant" })} testID="service-detail-book-via-chat">
        <Text style={s.bookBtnText}>Book via Chat</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:  { flex:1, backgroundColor:theme.colors.bg },
    label:   { fontSize:theme.font.size.xs, fontWeight:theme.font.weight.bold,
               color:theme.colors.textTertiary, textTransform:"uppercase", letterSpacing:1 },
    content: { padding:theme.spacing.base, gap:14, paddingBottom:40 },
    center:  { flex:1, alignItems:"center", justifyContent:"center", padding:32, gap:12 },
    icon:    { fontSize:44 },
    title:   { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
    body:    { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, textAlign:"center" },
    name:    { fontSize:theme.font.size.xxl, fontWeight:"800", color:theme.colors.textPrimary },
    category:{ fontSize:theme.font.size.sm, color:theme.colors.textTertiary, fontWeight:"600", textTransform:"uppercase" },
    description: { fontSize:theme.font.size.base, color:theme.colors.textSecondary, lineHeight:20 },
    price:   { fontSize:theme.font.size.xl, fontWeight:"800", color:theme.colors.brand },
    footnote:{ fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
    onSiteNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
    bookBtn: { backgroundColor:theme.colors.brand, borderRadius:theme.radius.lg, paddingVertical:14, alignItems:"center" },
    bookBtnText: { color:"#fff", fontWeight:"700", fontSize:theme.font.size.base },
  });
}
