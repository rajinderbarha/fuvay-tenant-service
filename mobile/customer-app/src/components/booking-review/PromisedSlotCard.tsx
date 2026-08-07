import React, { useState } from "react";
import { View, Modal, Pressable, ScrollView, ActivityIndicator } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { BookingReviewSummary, AvailableSlot } from "../../domain/bookingReview";

export interface PromisedSlotCardProps {
  slot: BookingReviewSummary["promisedSlot"];
  slaMinutes: number | null;
  availableSlots: AvailableSlot[] | null;
  slotsLoading: boolean;
  slotSelectionError: string | null;
  onOpenPicker: () => void;
  onSelectSlot: (dateIso: string, timeWindow: string) => Promise<void>;
}

/** Human day label for a promised slot, relative where that reads better. */
function dayLabel(dateIso: string, daysAhead: number): string {
  if (daysAhead === 0) return "Today";
  if (daysAhead === 1) return "Tomorrow";
  const d = new Date(`${dateIso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateIso;
  return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" });
}

/**
 * Shows WHEN the service will actually happen, before the customer commits.
 *
 * The provider owns capacity (their own business hours, slot length and
 * jobs-per-slot), so this slot is one they have genuinely got room for --
 * resolved today-first, then rolling forward day by day. Tapping "Change"
 * lets the customer pick a DIFFERENT real, capacity-checked slot instead
 * of only ever seeing the single system-earliest one -- the picker shows
 * exactly the same slots the provider would honour, re-validated at
 * selection time (see useBookingReviewController.selectSlot).
 *
 * When the backend cannot promise a slot (no configured availability, or
 * fully booked across the search horizon) this says so plainly rather than
 * inventing a date nobody agreed to.
 */
export function PromisedSlotCard({
  slot, slaMinutes, availableSlots, slotsLoading, slotSelectionError, onOpenPicker, onSelectSlot,
}: PromisedSlotCardProps) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);

  function openPicker() {
    setOpen(true);
    onOpenPicker();
  }

  async function handlePick(s: AvailableSlot) {
    const key = `${s.date}|${s.timeWindow}`;
    setSelecting(key);
    try {
      await onSelectSlot(s.date, s.timeWindow);
      setOpen(false);
    } catch {
      // Error surfaces via slotSelectionError below the list; the sheet
      // stays open so the customer can pick a different real slot rather
      // than being dropped back to the review screen.
    } finally {
      setSelecting(null);
    }
  }

  if (!slot) {
    return (
      <AppCard>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
          <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="labelStrong" color="secondary">Service time</AppText>
        </View>
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xs }}>
          We can&apos;t confirm a service time right now. Your provider will contact you to arrange one.
        </AppText>
      </AppCard>
    );
  }

  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
          <Icon name="time-outline" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
          <AppText variant="labelStrong" color="secondary">Your service will be done</AppText>
        </View>
        <Pressable onPress={openPicker} accessibilityRole="button" accessibilityLabel="Change service time">
          <AppText variant="labelStrong" color="link">Change</AppText>
        </Pressable>
      </View>

      <AppText variant="headingSmall" style={{ marginTop: theme.spacing.xs }}>
        {dayLabel(slot.date, slot.daysAhead)}, {slot.timeWindow}
      </AppText>

      {slaMinutes ? (
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
          {`Your provider has ${slaMinutes} minutes to complete the service once this window starts.`}
        </AppText>
      ) : null}

      <View style={{
        marginTop: theme.spacing.sm,
        paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs,
        borderRadius: theme.radiusUsage.input,
        backgroundColor: theme.colors.brandPrimaryMuted,
        flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
      }}>
        <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        <AppText variant="caption" style={{ color: theme.colors.brandPrimaryStrong, flex: 1 }}>
          This slot is reserved for you when you confirm — no waiting for a callback.
        </AppText>
      </View>

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          <View
            style={{
              backgroundColor: theme.colors.surfaceDefault,
              borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card,
              padding: theme.spacing.base, gap: theme.spacing.sm, maxHeight: "75%",
            }}
          >
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <AppText variant="headingSmall">Choose a time</AppText>
              <AppIconButton name="close" onPress={() => setOpen(false)} accessibilityLabel="Close" />
            </View>
            <AppText variant="bodySmall" color="secondary">
              Every time below is real -- your provider genuinely has room for it right now.
            </AppText>

            {slotSelectionError ? (
              <AppText variant="bodySmall" style={{ color: theme.colors.statusDanger }}>{slotSelectionError}</AppText>
            ) : null}

            {slotsLoading && !availableSlots ? (
              <ActivityIndicator color={theme.colors.brandPrimaryStrong} />
            ) : availableSlots && availableSlots.length === 0 ? (
              <AppText variant="bodySmall" color="secondary">
                No other times are available from this provider right now.
              </AppText>
            ) : (
              <ScrollView>
                <View style={{ gap: theme.spacing.xs }}>
                  {(availableSlots ?? []).map(s => {
                    const key = `${s.date}|${s.timeWindow}`;
                    const isCurrent = s.date === slot.date && s.timeWindow === slot.timeWindow;
                    const isBusy = selecting === key;
                    return (
                      <Pressable
                        key={key}
                        onPress={() => handlePick(s)}
                        disabled={isCurrent || selecting !== null}
                        accessibilityRole="button"
                        accessibilityLabel={`${dayLabel(s.date, s.daysAhead)}, ${s.timeWindow}${isCurrent ? ", currently selected" : ""}`}
                        style={{
                          flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                          minHeight: theme.touchTargets.comfortable,
                          paddingHorizontal: theme.spacing.base,
                          borderRadius: theme.radiusUsage.input,
                          borderWidth: 1, borderColor: isCurrent ? theme.colors.brandPrimary : theme.colors.borderSubtle,
                          backgroundColor: isCurrent ? theme.colors.brandPrimaryMuted : theme.colors.surfaceDefault,
                          opacity: selecting !== null && !isBusy ? 0.5 : 1,
                        }}
                      >
                        <AppText variant="body">{dayLabel(s.date, s.daysAhead)}, {s.timeWindow}</AppText>
                        {isBusy ? (
                          <ActivityIndicator size="small" color={theme.colors.brandPrimaryStrong} />
                        ) : isCurrent ? (
                          <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimary} decorative />
                        ) : null}
                      </Pressable>
                    );
                  })}
                </View>
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
    </AppCard>
  );
}
