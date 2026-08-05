import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerBookingEvent } from "../../domain/bookingActivity";

/** Renders only real derived events -- see domain/bookingActivity.ts for
 * why there is exactly one today (no fabricated "matching started" /
 * "provider notified" steps). */
export function BookingActivity({ events }: { events: CustomerBookingEvent[] }) {
  const { theme } = useTheme();
  if (events.length === 0) return null;
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Booking activity</AppText>
      <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>Activity</AppText>
      {events.map(event => (
        <View key={event.id} style={{ flexDirection: "row", gap: theme.spacing.xs, marginTop: theme.spacing.xs }}>
          <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
          <View style={{ flex: 1 }}>
            <AppText variant="body">{event.label}</AppText>
          </View>
        </View>
      ))}
    </AppCard>
  );
}
