import React, { useEffect, useMemo, useState } from "react";
import { Alert, Modal, Pressable, ScrollView, TextInput, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppButton } from "../AppButton";
import { AppCard } from "../AppCard";
import { AppText } from "../AppText";
import {
  BookingActionEligibility,
  cancelCustomerBooking,
  getBookingActionEligibility,
  getRescheduleAvailability,
  rescheduleCustomerBooking,
} from "../../api/customerBookings/customerBookingsApi";

type Mode = "cancel" | "reschedule" | null;

const reasonLabel = (value: string) => value.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());

export function BookingManageActions({ bookingId, onChanged }: { bookingId: string; onChanged: () => void }) {
  const { theme } = useTheme();
  const [eligibility, setEligibility] = useState<BookingActionEligibility | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<Mode>(null);
  const [reason, setReason] = useState("");
  const [detail, setDetail] = useState("");
  const [dates, setDates] = useState<Array<{ date: string; available: boolean }>>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [timeWindow, setTimeWindow] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const result = await getBookingActionEligibility(bookingId);
      setEligibility(result.data);
    } catch {
      setEligibility(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [bookingId]);

  const availableDates = useMemo(() => dates.filter(item => item.available), [dates]);
  const close = () => {
    if (submitting) return;
    setMode(null);
    setReason("");
    setDetail("");
    setSelectedDate("");
    setTimeWindow("");
  };

  const openReschedule = async () => {
    setMode("reschedule");
    try {
      const result = await getRescheduleAvailability(bookingId);
      setDates(result.data.dates);
    } catch {
      setDates([]);
      Alert.alert("Availability unavailable", "Please refresh and try again.");
    }
  };

  const submit = async () => {
    if (!eligibility || !reason.trim()) return;
    setSubmitting(true);
    try {
      if (mode === "cancel") {
        await cancelCustomerBooking(bookingId, {
          reason,
          detail: detail.trim() || undefined,
          expectedVersion: eligibility.version,
        });
        Alert.alert("Booking cancelled", "Your provider has been notified.");
      } else if (mode === "reschedule" && selectedDate) {
        await rescheduleCustomerBooking(bookingId, {
          scheduledDate: selectedDate,
          scheduledTimeWindow: timeWindow.trim() || undefined,
          reason: reason.trim(),
          expectedVersion: eligibility.version,
        });
        Alert.alert("Booking rescheduled", "Your provider has been notified of the new date.");
      }
      setMode(null);
      setReason("");
      setDetail("");
      setSelectedDate("");
      setTimeWindow("");
      await load();
      onChanged();
    } catch (error) {
      Alert.alert("Change not completed", error instanceof Error ? error.message : "Please refresh and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !eligibility || (!eligibility.can_cancel && !eligibility.can_reschedule)) return null;

  const inputStyle = {
    minHeight: theme.touchTargets.minimum,
    borderWidth: 1,
    borderColor: theme.colors.borderDefault,
    borderRadius: theme.radius.radiusMedium,
    paddingHorizontal: theme.spacing.sm,
    color: theme.colors.textPrimary,
    backgroundColor: theme.colors.surfaceDefault,
  } as const;

  return (
    <>
      <AppCard style={{ gap: theme.spacing.sm }}>
        <AppText variant="bodyStrong">Need to change your booking?</AppText>
        <AppText variant="bodySmall" color="secondary">
          Changes are checked against the provider's live availability and service policy.
        </AppText>
        {eligibility.can_reschedule ? (
          <AppButton label="Choose a new date" tone="secondary" fullWidth onPress={openReschedule} />
        ) : null}
        {eligibility.can_cancel ? (
          <AppButton label="Cancel booking" tone="destructive" fullWidth onPress={() => setMode("cancel")} />
        ) : null}
      </AppCard>

      <Modal visible={mode !== null} transparent animationType="slide" onRequestClose={close}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          <View style={{ maxHeight: "82%", padding: theme.spacing.base, gap: theme.spacing.sm, backgroundColor: theme.colors.backgroundElevated, borderTopLeftRadius: theme.radius.radiusLarge, borderTopRightRadius: theme.radius.radiusLarge }}>
            <AppText variant="title">{mode === "cancel" ? "Cancel booking" : "Choose a new date"}</AppText>
            <ScrollView contentContainerStyle={{ gap: theme.spacing.sm }} keyboardShouldPersistTaps="handled">
              {mode === "cancel" ? (
                <>
                  <AppText variant="bodySmall" color="secondary">Tell the provider why you are cancelling.</AppText>
                  <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs }}>
                    {eligibility.allowed_cancellation_reasons.map(item => (
                      <Pressable key={item} onPress={() => setReason(item)} style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs, borderRadius: theme.radius.radiusFull, borderWidth: 1, borderColor: reason === item ? theme.colors.brandPrimary : theme.colors.borderDefault, backgroundColor: reason === item ? theme.colors.surfaceSelected : theme.colors.surfaceDefault }}>
                        <AppText variant="bodySmall">{reasonLabel(item)}</AppText>
                      </Pressable>
                    ))}
                  </View>
                  {eligibility.cancellation_reasons_requiring_detail.includes(reason) ? (
                    <TextInput value={detail} onChangeText={setDetail} placeholder="Please explain" placeholderTextColor={theme.colors.textTertiary} multiline style={[inputStyle, { minHeight: 88, paddingTop: theme.spacing.sm }]} />
                  ) : null}
                </>
              ) : (
                <>
                  <AppText variant="bodySmall" color="secondary">Only dates with current provider capacity are shown.</AppText>
                  {availableDates.length ? (
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs }}>
                      {availableDates.map(item => (
                        <Pressable key={item.date} onPress={() => setSelectedDate(item.date)} style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs, borderRadius: theme.radius.radiusMedium, borderWidth: 1, borderColor: selectedDate === item.date ? theme.colors.brandPrimary : theme.colors.borderDefault, backgroundColor: selectedDate === item.date ? theme.colors.surfaceSelected : theme.colors.surfaceDefault }}>
                          <AppText variant="bodySmall">{new Date(`${item.date}T12:00:00`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</AppText>
                        </Pressable>
                      ))}
                    </View>
                  ) : <AppText variant="bodySmall">No available date was found in the next 14 days.</AppText>}
                  <TextInput value={timeWindow} onChangeText={setTimeWindow} placeholder="Preferred time, e.g. 10:00–12:00 (optional)" placeholderTextColor={theme.colors.textTertiary} style={inputStyle} />
                  <TextInput value={reason} onChangeText={setReason} placeholder="Reason for rescheduling" placeholderTextColor={theme.colors.textTertiary} style={inputStyle} />
                </>
              )}
            </ScrollView>
            <AppButton
              label={mode === "cancel" ? "Confirm cancellation" : "Confirm new date"}
              tone={mode === "cancel" ? "destructive" : "primary"}
              fullWidth
              loading={submitting}
              disabled={!reason.trim() || (mode === "cancel" && eligibility.cancellation_reasons_requiring_detail.includes(reason) && !detail.trim()) || (mode === "reschedule" && !selectedDate)}
              onPress={submit}
            />
            <AppButton label="Keep current booking" tone="tertiary" fullWidth disabled={submitting} onPress={close} />
          </View>
        </View>
      </Modal>
    </>
  );
}
