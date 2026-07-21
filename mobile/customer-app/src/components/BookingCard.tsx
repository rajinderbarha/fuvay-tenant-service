import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { JobStatusBadge } from "./JobStatusBadge";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";
import type { Booking } from "../lib/api";

interface Props { booking:Booking; onPress:()=>void }

// UX-06 Round 6 correction: `/v1/customer/bookings*` (home_service_assignment
// engine) returns issue_summary/city/selected_provider/selected_price_amount,
// not service_type/scheduled_at -- confirmed live this round by creating a
// real booking (BK-20260721-000001) and inspecting the actual list response.
//
// UX-07 Round 4 Pass 2: migrated to useTheme() for dark mode, added a real
// accessibilityLabel summarizing the card (service, booking number, status,
// price) so the whole tappable card reads as one coherent item, and made
// the row itself a real "button" activation target for keyboard/switch nav.
export function BookingCard({ booking:b, onPress }:Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const priceText = b.selected_price_amount != null ? `, ₹${b.selected_price_amount.toLocaleString("en-IN")}` : "";
  return (
    <TouchableOpacity style={s.card} onPress={onPress} activeOpacity={0.85}
      accessible accessibilityRole="button"
      accessibilityLabel={`${b.issue_summary ?? "Service"}, booking ${b.booking_number}${priceText}`}>
      <View style={s.top}>
        <View style={{ flex:1 }}>
          <Text style={s.serviceType} numberOfLines={1}>{b.issue_summary ?? "Service"}</Text>
          <Text style={s.meta}>{b.booking_number}{b.city ? ` · ${b.city}` : ""}</Text>
        </View>
        <JobStatusBadge status={b.status} size="sm" />
      </View>
      {b.selected_provider?.provider_name && (
        <View style={s.dateRow}>
          <Text style={s.dateIcon}>🏢</Text>
          <Text style={s.dateText}>{b.selected_provider.provider_name}</Text>
        </View>
      )}
      {b.selected_price_amount != null && (
        <Text style={s.price}>₹{b.selected_price_amount.toLocaleString("en-IN")}</Text>
      )}
    </TouchableOpacity>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    card:     { backgroundColor:theme.colors.surfaceCard, borderRadius:theme.radius.lg, padding:14, ...theme.shadow.sm },
    top:      { flexDirection:"row", alignItems:"flex-start", gap:10, marginBottom:10 },
    serviceType:{ fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
    meta:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:3 },
    dateRow:  { flexDirection:"row", alignItems:"center", gap:6, marginBottom:4 },
    dateIcon: { fontSize:14 },
    dateText: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
    price:    { fontSize:theme.font.size.base, fontWeight:"800", color:theme.colors.brand, marginTop:4 },
  });
}
