import React, { useCallback, useState } from "react";
import { Alert, Modal, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useApi, useAction } from "../hooks/useApi";
import { bookingsApi } from "../lib/api";
import { JobStatusBadge } from "../components/JobStatusBadge";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { isTrackable, needsReview } from "../lib/jobStatus";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { bookingId:string };
type Props  = NativeStackScreenProps<{ BookingDetail:Params }, "BookingDetail">;

export function BookingDetailScreen({ route, navigation }: Props) {
  const { bookingId } = route.params;
  const [cancelModal, setCancelModal] = useState(false);
  const [reason,      setReason]      = useState("");

  const booking     = useApi(useCallback(() => bookingsApi.get(bookingId), [bookingId]));
  const cancelAction = useAction(useCallback(
    (r:string) => bookingsApi.cancel(bookingId, r), [bookingId]
  ));

  const b = booking.data;
  const fmtDate = (d:string) => new Date(d).toLocaleString("en-IN",{weekday:"short",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"});

  async function handleCancel() {
    if (!reason.trim()) { Alert.alert("Required","Please provide a cancellation reason."); return; }
    const res = await cancelAction.execute(reason.trim());
    if (res) { setCancelModal(false); booking.refetch(); }
  }

  if (booking.loading) return (
    <ScrollView style={gs.screen} contentContainerStyle={{padding:theme.spacing.base,gap:14}}>
      {[...Array(3)].map((_,i)=><Skeleton key={i} height={90}/>)}
    </ScrollView>
  );

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content}>
      {b && (
        <>
          {/* Status header */}
          <Card style={{ gap:10 }}>
            <View style={[gs.row,{justifyContent:"space-between"}]}>
              <Text style={s.bookingNum}>{b.booking_number}</Text>
              <JobStatusBadge status={b.status}/>
            </View>
            <Text style={s.serviceType}>{b.service_type}</Text>
            <Text style={s.date}>📅 {fmtDate(b.scheduled_at)}</Text>
            {b.price_snapshot && (
              <Text style={s.price}>₹{b.price_snapshot.final_price.toLocaleString("en-IN")}</Text>
            )}
          </Card>

          {/* Credit + direct-payment breakdown — customer pays the provider
              directly on-site; ServiceOS never collects the service payment. */}
          {b.quoted_price != null && (
            <Card style={{ gap:8 }}>
              <Text style={gs.label}>Payment Breakdown</Text>
              <View style={s.row}>
                <Text style={s.rowLabel}>Service Price</Text>
                <Text style={s.rowValue}>₹{b.quoted_price.toLocaleString("en-IN")}</Text>
              </View>
              {!!b.credit_applied && (
                <View style={s.row}>
                  <Text style={s.rowLabel}>ServiceOS Credit Used</Text>
                  <Text style={s.rowValue}>₹{b.credit_applied.toLocaleString("en-IN")}</Text>
                </View>
              )}
              <View style={s.row}>
                <Text style={[s.rowLabel,{fontWeight:"700"}]}>Paid Directly To Provider</Text>
                <Text style={[s.rowValue,{fontWeight:"700",color:theme.colors.brand}]}>
                  ₹{(b.payable_amount ?? b.quoted_price).toLocaleString("en-IN")}
                </Text>
              </View>
              <Text style={s.footnote}>
                You will pay the remaining amount directly to the provider after service completion.
              </Text>
            </Card>
          )}

          {/* Provider info */}
          {(b.tenant_name || b.assigned_staff) && (
            <Card style={{ gap:8 }}>
              <Text style={gs.label}>Service Provider</Text>
              {b.tenant_name   && <Text style={s.provText}>🏢 {b.tenant_name}</Text>}
              {b.assigned_staff&& <Text style={s.provText}>👨‍🔧 {b.assigned_staff}</Text>}
            </Card>
          )}

          {/* Notes */}
          {b.notes && (
            <Card>
              <Text style={gs.label}>Your Notes</Text>
              <Text style={s.notes}>{b.notes}</Text>
            </Card>
          )}

          {/* CTA buttons */}
          <View style={{ gap:10 }}>
            {b.status === "quote_sent" && (
              <Button label="⚠ Review Repair Quote" variant="primary" size="lg" fullWidth
                onPress={()=>navigation.navigate("QuoteApproval" as never,{jobId:b.id,bookingNumber:b.booking_number} as never)}/>
            )}
            {isTrackable(b.status) && (
              <Button label="Track Technician 📍" variant="primary" size="lg" fullWidth
                onPress={()=>navigation.navigate("JobTracking" as never,{bookingId:b.id} as never)}/>
            )}
            {needsReview(b.status) && (
              <Button label="Leave a Review ⭐" variant="outline" size="lg" fullWidth
                onPress={()=>navigation.navigate("Review" as never,{bookingId:b.id} as never)}/>
            )}
            {["pending_confirmation","confirmed"].includes(b.status) && (
              <Button label="Cancel Booking" variant="danger" size="md" fullWidth
                onPress={()=>setCancelModal(true)}/>
            )}
          </View>
        </>
      )}

      {/* Cancel modal */}
      <Modal visible={cancelModal} transparent animationType="slide" onRequestClose={()=>setCancelModal(false)}>
        <View style={s.overlay}>
          <View style={s.sheet}>
            <Text style={s.modalTitle}>Cancel Booking</Text>
            <Text style={s.modalSub}>Please tell us why you want to cancel.</Text>
            <TextInput style={s.textarea} value={reason} onChangeText={setReason}
              placeholder="e.g. Plans changed, rescheduling for later…"
              placeholderTextColor={theme.colors.textTertiary}
              multiline numberOfLines={4} textAlignVertical="top"/>
            {cancelAction.error&&<Text style={s.errText}>{cancelAction.error}</Text>}
            <View style={{gap:10}}>
              <Button label="Confirm Cancellation" variant="danger" size="lg"
                loading={cancelAction.loading} onPress={handleCancel} fullWidth/>
              <Button label="Keep Booking" variant="ghost" size="md"
                onPress={()=>setCancelModal(false)} fullWidth/>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:    { padding:theme.spacing.base, gap:12, paddingBottom:40 },
  bookingNum: { fontSize:theme.font.size.base, fontWeight:"700", color:theme.colors.textPrimary },
  serviceType:{ fontSize:theme.font.size.xl,  fontWeight:"700", color:theme.colors.textPrimary },
  date:       { fontSize:theme.font.size.base, color:theme.colors.textSecondary },
  price:      { fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.brand },
  provText:   { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
  row:        { flexDirection:"row", justifyContent:"space-between" },
  rowLabel:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  rowValue:   { fontSize:theme.font.size.sm, color:theme.colors.textPrimary, fontWeight:"600" },
  footnote:   { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, marginTop:2 },
  notes:      { fontSize:theme.font.size.base, color:theme.colors.textSecondary, lineHeight:22 },
  overlay:    { flex:1, justifyContent:"flex-end", backgroundColor:"rgba(0,0,0,0.45)" },
  sheet:      { backgroundColor:theme.colors.surface, borderTopLeftRadius:28, borderTopRightRadius:28,
                padding:24, gap:14, paddingBottom:40 },
  modalTitle: { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary },
  modalSub:   { fontSize:theme.font.size.sm, color:theme.colors.textSecondary },
  textarea:   { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                minHeight:90, backgroundColor:theme.colors.surfaceSunken },
  errText:    { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
});
