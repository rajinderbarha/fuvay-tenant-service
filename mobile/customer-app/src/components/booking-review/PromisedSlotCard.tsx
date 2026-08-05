import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { BookingReviewSummary } from "../../domain/bookingReview";

export interface PromisedSlotCardProps {
  slot: BookingReviewSummary["promisedSlot"];
  slaMinutes: number | null;
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
 * resolved today-first, then rolling forward day by day. The customer makes
 * the final call on a real promise instead of confirming blind and waiting
 * to find out.
 *
 * When the backend cannot promise a slot (no configured availability, or
 * fully booked across the search horizon) this says so plainly rather than
 * inventing a date nobody agreed to.
 */
export function PromisedSlotCard({ slot, slaMinutes }: PromisedSlotCardProps) {
  const { theme } = useTheme();

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
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
        <Icon name="time-outline" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        <AppText variant="labelStrong" color="secondary">Your service will be done</AppText>
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
    </AppCard>
  );
}
