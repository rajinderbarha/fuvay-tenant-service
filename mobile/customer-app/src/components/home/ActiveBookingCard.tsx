import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../index";
import { Icon } from "../Icon";
import { HomeActiveBooking } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";

export interface ActiveBookingCardProps {
  booking: HomeActiveBooking;
  onPress: () => void;
  /** Category mascot for this booking, if we can resolve one from
   * `bookableCategories` by name match -- purely cosmetic, never changes
   * what data is shown (see HomeScreen, the only caller). */
  iconUrl?: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  pending_assignment: "Finding technician",
  assigned: "Assigned",
  scheduled: "Scheduled",
  on_the_way: "On the way",
  arrived: "Arrived",
  inspection: "Inspection",
  in_progress: "In progress",
  service_started: "In progress",
  awaiting_payment: "Payment pending",
  payment_pending: "Payment pending",
};

/**
 * Layout matches the reference design's Active Booking card: mascot,
 * title + subtitle, a status pill in the top-right corner, and a filled
 * circular arrow button -- built with this app's own theme tokens
 * (brandPrimary, surface colours), not new hardcoded colours.
 *
 * Renders only real fields the Home aggregation endpoint returns (see
 * domain/customerHome.ts HomeActiveBooking) -- no technician identity,
 * live ETA, price, or rating is fabricated. The reference design shows a
 * "Starting at ₹NNN" price row; this payload has no price field for an
 * active booking, so that row is simply absent rather than guessed.
 */
export function ActiveBookingCard({ booking, onPress, iconUrl }: ActiveBookingCardProps) {
  const { theme } = useTheme();
  const title = booking.issueSummary || booking.bookingNumber || "Your booking";
  const subtitleParts = [
    booking.providerName,
    booking.preferredDate ? new Date(booking.preferredDate).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : null,
    booking.preferredTimeWindow,
  ].filter((p): p is string => Boolean(p));
  const subtitle = subtitleParts.join(" · ") || (booking.bookingNumber && booking.issueSummary ? booking.bookingNumber : null);

  return (
    <View>
      {/* "Active Booking" at headingSmall to match the other section
          headers -- this was "My Booking" at bodyStrong, i.e. the same
          weight as the card title directly beneath it. */}
      <AppText variant="headingSmall" style={{ marginBottom: theme.spacing.sm }}>Active Booking</AppText>
      <View
        accessible
        accessibilityRole="button"
        accessibilityLabel={`Booking ${booking.bookingNumber ?? booking.bookingId}, status ${booking.status}`}
        onTouchEnd={onPress}
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
          padding: theme.spacing.base, borderRadius: theme.radiusUsage.card,
          backgroundColor: theme.colors.surfaceDefault, borderWidth: 1, borderColor: theme.colors.borderSubtle,
          // Badge below is an absolutely-positioned child of THIS card, not
          // a sibling of it -- anchoring it to the outer wrapper (which
          // also contains the "My Booking" label above) would need a
          // top-offset that accounts for that label's height, and any
          // future copy change above would silently misplace it.
          position: "relative",
        }}
      >
        <View
          style={{
            width: 56, height: 56, borderRadius: theme.radiusUsage.input,
            backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center",
            overflow: "hidden", flexShrink: 0,
          }}
        >
          {iconUrl ? (
            <Image source={{ uri: resolveMediaUrl(iconUrl)! }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
          ) : (
            <Icon name="construct-outline" size="navigation" color={theme.colors.brandPrimaryStrong} decorative />
          )}
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{title}</AppText>
          {subtitle ? (
            <AppText variant="caption" color="secondary" numberOfLines={1} style={{ marginTop: 1 }}>{subtitle}</AppText>
          ) : null}
        </View>
        <View
          style={{
            width: 36, height: 36, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimary, alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}
        >
          <Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />
        </View>
        <View
          style={{
            position: "absolute", top: -8, right: theme.spacing.sm,
            backgroundColor: theme.colors.textPrimary, borderRadius: theme.radiusUsage.statusPill,
            paddingHorizontal: theme.spacing.sm, paddingVertical: 3,
          }}
        >
          <AppText variant="labelStrong" style={{ color: theme.colors.textInverse }}>
            {STATUS_LABEL[booking.status] ?? booking.status.replace(/_/g, " ")}
          </AppText>
        </View>
      </View>
    </View>
  );
}
