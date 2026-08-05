import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText, AppCard, AppBadge } from "../index";
import { Icon } from "../Icon";
import { HomeActiveBooking } from "../../domain/customerHome";

export interface ActiveBookingCardProps {
  booking: HomeActiveBooking;
  onPress: () => void;
}

/**
 * Renders ONLY the fields the real Home aggregation endpoint returns
 * (booking_id, booking_number, status, created_at -- see
 * domain/customerHome.ts HomeActiveBooking). Deliberately has no
 * technician/ETA/rating/schedule props to fill in -- the Active Booking
 * Rule explicitly forbids fabricating any of those, and the type system
 * here makes it impossible to pass them by mistake.
 */
export function ActiveBookingCard({ booking, onPress }: ActiveBookingCardProps) {
  const { theme } = useTheme();
  return (
    <View>
      <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>My Booking</AppText>
      <AppCard>
        <View
          accessible
          accessibilityRole="button"
          accessibilityLabel={`Booking ${booking.bookingNumber ?? booking.bookingId}, status ${booking.status}`}
          onTouchEnd={onPress}
          style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}
        >
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radiusUsage.input,
              backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
            }}
          >
            <Icon name="construct-outline" size="navigation" color={theme.colors.iconDefault} decorative />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">{booking.bookingNumber ?? "Booking"}</AppText>
            <AppBadge label={booking.status.replace(/_/g, " ")} tone="info" />
          </View>
          <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
        </View>
      </AppCard>
    </View>
  );
}
