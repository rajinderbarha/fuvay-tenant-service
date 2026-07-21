import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { bookingsApi } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { bookingId:string };
type RootParamList = { BookingDetail: Params };
type Props  = NativeStackScreenProps<RootParamList, "BookingDetail">;

/**
 * UX-06 Round 6 correction: `GET /v1/customer/bookings/{id}` is backed by
 * `app/engines/home_service_assignment/customer_router.py` (engine_id:
 * "assignment") — confirmed by creating a REAL booking this round
 * (BK-20260721-000001, via an existing already-configured offering,
 * ac_installation, proving the full canonical pipeline end-to-end without
 * creating new shared pricing policy — see canonical-booking-live-evidence.md).
 * Real fields: booking_id/booking_number/status/issue_summary/city/
 * selected_provider/selected_price_option/selected_price_amount/
 * payment_mode/job_id/job_status/assignment_status/assignment_message.
 * Preserves pipeline identity: booking_id and job_id are shown as distinct,
 * secondary reference lines, never merged into one ID.
 *
 * UX-07 Pass 3b: migrated off the static `theme`/`gs` import onto useTheme().
 */
export function BookingDetailScreen({ route }: Props) {
  const { theme } = useTheme();
  const s = makeStyles(theme);
  const { bookingId } = route.params;
  const booking = useApi(useCallback(() => bookingsApi.get(bookingId), [bookingId]));
  const b = booking.data;

  if (booking.loading) return (
    <ScrollView style={s.screen} contentContainerStyle={{padding:theme.spacing.base,gap:14}}>
      {[...Array(3)].map((_,i)=><Skeleton key={i} height={90}/>)}
    </ScrollView>
  );

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      {b && (
        <>
          <Card style={{ gap:10 }}>
            <View style={[s.row,{justifyContent:"space-between"}]}>
              <Text style={s.bookingNum}>{b.booking_number ?? "Booking"}</Text>
              <JobStatusBadge status={b.status}/>
            </View>
            {b.issue_summary && <Text style={s.serviceType}>{b.issue_summary}</Text>}
            {b.city && <Text style={s.date}>📍 {b.city}</Text>}
            {b.selected_provider?.provider_name && (
              <Text style={s.date}>🏢 {b.selected_provider.provider_name}</Text>
            )}
            {b.assignment_message && <Text style={s.date}>{b.assignment_message}</Text>}
          </Card>

          {b.selected_price_amount != null && (
            <Card style={{ gap:6 }}>
              <View style={[s.row,{justifyContent:"space-between"}]}>
                <Text style={s.label}>Price</Text>
                <Text style={s.price}>₹{b.selected_price_amount.toLocaleString("en-IN")}</Text>
              </View>
              <Text style={s.onSiteNote}>
                Payment is made directly to the technician on-site — ServiceOS
                does not process this payment.
              </Text>
            </Card>
          )}

          {/* Pipeline provenance — kept as small, distinct secondary lines,
              never merged, never a primary label. */}
          <Card style={{ gap:4 }}>
            <Text style={s.internalId}>Booking ref: {b.booking_id}</Text>
            {b.job_id && <Text style={s.internalId}>Job ref: {b.job_id}{b.job_status ? ` (${b.job_status})` : ""}</Text>}
          </Card>
        </>
      )}
    </ScrollView>
  );
}

function makeStyles(theme: Theme) {
  return StyleSheet.create({
    screen:     { flex:1, backgroundColor:theme.colors.bg },
    row:        { flexDirection:"row", alignItems:"center" },
    label:      { fontSize:theme.font.size.xs, fontWeight:theme.font.weight.bold,
                  color:theme.colors.textTertiary, textTransform:"uppercase", letterSpacing:1 },
    content:    { padding:theme.spacing.base, gap:12, paddingBottom:40 },
    bookingNum: { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
    serviceType:{ fontSize:theme.font.size.xl,  fontWeight:"700", color:theme.colors.textPrimary },
    date:       { fontSize:theme.font.size.base, color:theme.colors.textSecondary },
    price:      { fontSize:theme.font.size.xl, fontWeight:"800", color:theme.colors.brand },
    internalId: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
    onSiteNote: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  });
}
