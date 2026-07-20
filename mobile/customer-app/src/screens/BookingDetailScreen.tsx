import React, { useCallback } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useApi } from "../hooks/useApi";
import { bookingsApi } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { bookingId:string };
type RootParamList = { BookingDetail: Params };
type Props  = NativeStackScreenProps<RootParamList, "BookingDetail">;

/**
 * UX-06 Round 5 rewrite. Two real, corrected issues found this round:
 * 1. This screen previously read fields (`price_snapshot`, `quoted_price`,
 *    `credit_applied`, `payable_amount`, `tenant_name`, `assigned_staff`)
 *    that were never confirmed to exist on the real `GET /v1/customer/bookings/{id}`
 *    response (Booking type in lib/api.ts only has id/booking_number/
 *    service_type/scheduled_at/status/created_at/notes) — trimmed to real
 *    fields only, removing the fabricated payment-breakdown card.
 * 2. It called `bookingsApi.cancel(...)`, which was never a real export —
 *    cancellation for this pipeline is deliberately UNRESOLVED/unexposed per
 *    the canonical domain rule established in Round 1 (see
 *    known-limitations.md history) — REMOVED the cancel button/modal
 *    entirely rather than leave a dead control calling a nonexistent
 *    endpoint. Same for the quote-approval/job-tracking/review CTAs, which
 *    referenced fields/routes not present on this real Booking shape — removed
 *    pending a real, confirmed contract (see production-route-design-census.csv).
 *
 * Preserves pipeline identity per Workstream 9: shows the real
 * booking_number/status/service_type/date, with the internal booking `id`
 * kept out of the primary label (shown only in a small secondary line).
 */
export function BookingDetailScreen({ route }: Props) {
  const { bookingId } = route.params;
  const booking = useApi(useCallback(() => bookingsApi.get(bookingId), [bookingId]));
  const b = booking.data;
  const fmtDate = (d?:string) => d ? new Date(d).toLocaleString("en-IN",{weekday:"short",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"}) : "Not yet scheduled";

  if (booking.loading) return (
    <ScrollView style={gs.screen} contentContainerStyle={{padding:theme.spacing.base,gap:14}}>
      {[...Array(3)].map((_,i)=><Skeleton key={i} height={90}/>)}
    </ScrollView>
  );

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {b && (
        <>
          <Card style={{ gap:10 }}>
            <View style={[gs.row,{justifyContent:"space-between"}]}>
              <Text style={s.bookingNum}>{b.booking_number ?? "Booking"}</Text>
              <JobStatusBadge status={b.status}/>
            </View>
            {b.service_type && <Text style={s.serviceType}>{b.service_type}</Text>}
            <Text style={s.date}>📅 {fmtDate(b.scheduled_at)}</Text>
            <Text style={s.internalId}>Ref: {b.id}</Text>
          </Card>

          <Card>
            <Text style={s.onSiteNote}>
              Payment is made directly to the technician on-site — ServiceOS
              does not process this payment.
            </Text>
          </Card>

          {b.notes && (
            <Card>
              <Text style={gs.label}>Your Notes</Text>
              <Text style={s.notes}>{b.notes}</Text>
            </Card>
          )}
        </>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:    { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  bookingNum: { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  serviceType:{ fontSize:theme.font.size.xl,  fontWeight:"700", color:theme.colors.textPrimary },
  date:       { fontSize:theme.font.size.base, color:theme.colors.textSecondary },
  internalId: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
  onSiteNote: { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  notes:      { fontSize:theme.font.size.base, color:theme.colors.textSecondary, lineHeight:22 },
});
