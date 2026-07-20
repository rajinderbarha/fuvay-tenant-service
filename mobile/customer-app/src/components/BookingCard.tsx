import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { JobStatusBadge } from "./JobStatusBadge";
import { theme } from "../styles/theme";
import type { Booking } from "../lib/api";

interface Props { booking:Booking; onPress:()=>void }

// UX-06 Round 5: trimmed to the real Booking shape (id/booking_number/
// service_type/scheduled_at/status/created_at/notes) -- price_snapshot/
// tenant_name/assigned_staff were never confirmed real fields (see
// BookingDetailScreen.tsx's Round 5 rewrite for the same correction).
export function BookingCard({ booking:b, onPress }:Props) {
  const date = b.scheduled_at ? new Date(b.scheduled_at) : null;
  const fmt  = date ? date.toLocaleDateString("en-IN",{ weekday:"short", day:"numeric", month:"short" }) : null;
  const time = date ? date.toLocaleTimeString("en-IN",{ hour:"2-digit", minute:"2-digit" }) : null;

  return (
    <TouchableOpacity style={s.card} onPress={onPress} activeOpacity={0.85}>
      <View style={s.top}>
        <View style={{ flex:1 }}>
          <Text style={s.serviceType}>{b.service_type ?? "Service"}</Text>
          <Text style={s.meta}>{b.booking_number}</Text>
        </View>
        <JobStatusBadge status={b.status} size="sm" />
      </View>
      {date && (
        <View style={s.dateRow}>
          <Text style={s.dateIcon}>📅</Text>
          <Text style={s.dateText}>{fmt} at {time}</Text>
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
  dateIcon: { fontSize:14 },
  dateText: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
});
