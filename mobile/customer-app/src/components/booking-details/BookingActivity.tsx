import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerBookingEvent } from "../../domain/bookingActivity";
import { formatCreatedAt } from "../../domain/dates";

/** Renders only real derived events -- see domain/bookingActivity.ts for
 * why there is exactly one today (no fabricated "matching started" /
 * "provider notified" steps).
 *
 * `deriveBookingActivity` is documented as producing exactly one event
 * kind ("the ONLY event this phase may ever produce"), always meaning the
 * request was confirmed -- so a fixed title line is safe here, not a
 * guess: it is the one true description of what this event always is.
 * `event.label` (the backend-derived sentence) is shown as the supporting
 * line beneath it, verbatim.
 *
 * Renders as a live timeline, not a static list: the connector line runs
 * past the LAST real event too (in a fainter tone), signalling that this
 * feed keeps going as the booking progresses -- it does not claim a next
 * event exists, only that the timeline itself continues. */
export interface BookingActivityProps {
  events: CustomerBookingEvent[];
  /** Skip the surrounding AppCard -- the design shows this section and
   * BookingUpdatesCard as one continuous card divided by a hairline, so
   * BookingDetailsScreen wraps both itself rather than each rendering
   * its own border. */
  bare?: boolean;
}

export function BookingActivity({ events, bare = false }: BookingActivityProps) {
  const { theme } = useTheme();
  if (events.length === 0) return null;
  const content = (
    <>
      <AppText variant="labelStrong" color="secondary">Booking activity</AppText>
      <View style={{ marginTop: theme.spacing.sm }}>
        {events.map((event, i) => (
          <View key={event.id} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            <View style={{ alignItems: "center" }}>
              <View
                style={{
                  width: 24, height: 24, borderRadius: theme.radius.radiusFull,
                  backgroundColor: theme.colors.statusSuccess,
                  alignItems: "center", justifyContent: "center",
                }}
              >
                <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative />
              </View>
              {/* Continues past the last event too, faded, so the feed
                  reads as ongoing rather than finished. */}
              <View
                style={{
                  width: 2, flex: 1, minHeight: 16,
                  backgroundColor: theme.colors.borderSubtle,
                  opacity: i < events.length - 1 ? 1 : 0.4,
                }}
              />
            </View>
            <View style={{ flex: 1, paddingBottom: theme.spacing.sm }}>
              <AppText variant="bodyStrong">Service request confirmed</AppText>
              <AppText variant="caption" color="tertiary">{formatCreatedAt(event.timestamp)}</AppText>
              <AppText variant="bodySmall" color="secondary" style={{ marginTop: 1 }}>{event.label}</AppText>
            </View>
          </View>
        ))}
      </View>
    </>
  );
  return bare ? content : <AppCard>{content}</AppCard>;
}
