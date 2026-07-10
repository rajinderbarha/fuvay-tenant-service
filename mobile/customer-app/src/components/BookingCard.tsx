import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { JobStatusBadge } from "./JobStatusBadge";
import { theme } from "../styles/theme";
import type { Booking } from "../lib/api";

interface Props { booking:Booking; onPress:()=>void }

export function BookingCard({ booking:b, onPress }:Props) {
  const date = new Date(b.scheduled_at);
  const fmt  = date.toLocaleDateString("en-IN",{ weekday:"short", day:"numeric", month:"short" });
  const time = date.toLocaleTimeString("en-IN",{ hour:"2-digit", minute:"2-digit" });

  return (
    <TouchableOpacity style={s.card} onPress={onPress} activeOpacity={0.85}>
      <View style={s.top}>
        <View style={{ flex:1 }}>
          <Text style={s.serviceType}>{b.service_type}</Text>
          <Text style={s.meta}>{b.booking_number}{b.tenant_name?` · ${b.tenant_name}`:""}</Text>
        </View>
        <JobStatusBadge status={b.status} size="sm" />
      </View>
      <View style={s.dateRow}>
        <Text style={s.dateIcon}>📅</Text>
        <Text style={s.dateText}>{fmt} at {time}</Text>
      </View>
      {b.assigned_staff && (
        <View style={s.staffRow}>
          <Text style={s.dateIcon}>👨‍🔧</Text>
          <Text style={s.staffText}>{b.assigned_staff}</Text>
        </View>
      )}
      {b.price_snapshot && (
        <View style={s.priceRow}>
          <Text style={s.price}>₹{b.price_snapshot.final_price.toLocaleString("en-IN")}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  card:     { backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg, padding:14, ...theme.shadow.sm },
  top:      { flexDirection:"row", alignItems:"flex-start", gap:10, marginBottom:10 },
  serviceType:{ fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
  meta:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:3 },
  dateRow:  { flexDirection:"row", alignItems:"center", gap:6, marginBottom:4 },
  staffRow: { flexDirection:"row", alignItems:"center", gap:6, marginBottom:4 },
  dateIcon: { fontSize:14 },
  dateText: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  staffText:{ fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  priceRow: { marginTop:6, alignItems:"flex-end" },
  price:    { fontSize:theme.font.size.lg, fontWeight:"800", color:theme.colors.brand },
});
