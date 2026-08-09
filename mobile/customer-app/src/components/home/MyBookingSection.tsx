import React from "react";
import { View, Image, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../index";
import { Icon } from "../Icon";
import { HomeActiveBooking } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { interpretBookingStatus } from "../../domain/bookingStatus";

export interface MyBookingSectionProps {
  booking: HomeActiveBooking;
  onPress: () => void;
  onViewAll: () => void;
  /** Category mascot for this booking, if one can be resolved from
   * `bookableCategories` by name -- purely cosmetic, never changes what
   * data is shown. */
  iconUrl?: string | null;
}

/**
 * "My Booking" strip on Home: the one live job, with a "View All" link
 * into the bookings tab.
 *
 * Shows who is doing the work -- the provider, their verification tick, their
 * earned rating and their awarded badges -- plus the slot they committed to.
 * The provider comes from the same two backend functions the booking-review
 * card uses, so a provider cannot read one way while being booked and another
 * way once the job is live.
 *
 * Every line is real backend data (see HomeActiveBooking). Two things the
 * reference design shows are NOT rendered, because nothing in this system
 * produces them:
 *
 *  - a live ETA ("Arriving in 15 MIN"). Technician coordinates and the
 *    destination both exist on the tracking endpoint, but no ETA is ever
 *    computed from them; deriving one here from an assumed travel speed
 *    would be a number the app invented and the customer would plan
 *    around.
 *  - a star rating when the technician has none. The rating is real
 *    (staff_rating_summaries) but null until they have actually been
 *    reviewed, and an unearned star is worse than no star.
 *
 * Each row is omitted when its data is absent rather than filled with a
 * placeholder, so the card shrinks to what is genuinely known.
 */
export function MyBookingSection({ booking, onPress, onViewAll, iconUrl }: MyBookingSectionProps) {
  const { theme } = useTheme();

  // Same adapter the bookings list uses, so a status never reads one way
  // on Home and another way on the Bookings tab.
  const { statusLabel } = interpretBookingStatus(booking.status, booking.assignmentStatus ?? "");
  const title = booking.serviceName || booking.issueSummary || booking.bookingNumber || "Your booking";

  // The COMMITTED slot when there is one, falling back to what the customer
  // asked for. Never mixed: `scheduledFor` says which of the two this is, so
  // "Requested" is never shown as though the provider had agreed to it.
  const scheduled = booking.scheduledDate || booking.scheduledTimeWindow;
  const scheduleLabel = scheduled
    ? formatSchedule(booking.scheduledDate, booking.scheduledTimeWindow)
    : formatSchedule(booking.preferredDate, booking.preferredTimeWindow);
  const technician = booking.technician;
  const provider = booking.provider;
  const providerName = provider?.name ?? booking.providerName ?? null;
  const providerRating = provider?.rating ?? null;
  // Two at most: a third chip wraps the row on a narrow phone and pushes the
  // slot line out of the card.
  const badges = (provider?.badges ?? []).slice(0, 2);

  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: theme.spacing.sm }}>
        <AppText variant="headingSmall">My Booking</AppText>
        <Pressable
          onPress={onViewAll}
          accessibilityRole="button"
          accessibilityLabel="View all bookings"
          hitSlop={8}
          style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
        >
          <AppText variant="labelStrong" color="link">View All</AppText>
          <Icon name="arrow-forward" size="compact" color={theme.colors.brandPrimary} decorative />
        </Pressable>
      </View>

      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={[
          title, statusLabel,
          providerName ? `provider ${providerName}` : null,
          technician?.name ? `technician ${technician.name}` : null,
          scheduleLabel,
        ].filter(Boolean).join(", ")}
        style={({ pressed }) => ({
          flexDirection: "row", gap: theme.spacing.sm,
          padding: theme.spacing.base,
          borderRadius: theme.radiusUsage.card,
          backgroundColor: theme.colors.surfaceDefault,
          borderWidth: 1, borderColor: theme.colors.borderSubtle,
          opacity: pressed ? 0.9 : 1,
          ...theme.shadow.sm,
        })}
      >
        <View
          style={{
            width: 52, height: 52, borderRadius: theme.radiusUsage.input,
            backgroundColor: theme.colors.brandPrimaryMuted,
            alignItems: "center", justifyContent: "center",
            overflow: "hidden", flexShrink: 0,
          }}
        >
          {iconUrl ? (
            <Image source={{ uri: resolveMediaUrl(iconUrl)! }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
          ) : (
            <Icon name="snow-outline" size="navigation" color={theme.colors.brandPrimaryStrong} decorative />
          )}
        </View>

        <View style={{ flex: 1, minWidth: 0, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{title}</AppText>

          {/* Who is doing the work: the provider, with their verification and
              earned rating. The technician is named alongside once one is
              actually assigned -- before that the provider is the only real
              answer to "who". */}
          {providerName ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexWrap: "wrap" }}>
              <AppText variant="caption" color="secondary" numberOfLines={1}>{providerName}</AppText>
              {provider?.verified ? (
                <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimary} decorative />
              ) : null}
              {providerRating != null ? (
                <>
                  <Icon name="star" size="compact" color={theme.colors.statusWarning} decorative />
                  <AppText variant="caption" color="secondary">{providerRating.toFixed(1)}</AppText>
                </>
              ) : null}
              {technician?.name ? (
                <AppText variant="caption" color="tertiary" numberOfLines={1}>· {technician.name}</AppText>
              ) : null}
            </View>
          ) : technician?.name ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
              <AppText variant="caption" color="secondary" numberOfLines={1}>{technician.name}</AppText>
              {technician.rating != null ? (
                <>
                  <Icon name="star" size="compact" color={theme.colors.statusWarning} decorative />
                  <AppText variant="caption" color="secondary">{technician.rating.toFixed(1)}</AppText>
                </>
              ) : null}
            </View>
          ) : null}

          {/* Backend-awarded badges only, capped at two so the row stays one
              line on a narrow phone. Empty renders nothing. */}
          {badges.length > 0 ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexWrap: "wrap" }}>
              {badges.map(badge => (
                <View
                  key={badge.name}
                  style={{
                    paddingVertical: 2, paddingHorizontal: theme.spacing.xs,
                    borderRadius: theme.radiusUsage.statusPill,
                    backgroundColor: theme.colors.surfaceInteractive,
                  }}
                >
                  <AppText variant="caption" color="link" numberOfLines={1}>{badge.name}</AppText>
                </View>
              ))}
            </View>
          ) : null}

          {scheduleLabel ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
              <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
              <AppText variant="caption" color="secondary" numberOfLines={1}>{scheduleLabel}</AppText>
            </View>
          ) : null}
        </View>

        <View style={{ alignItems: "flex-end", flexShrink: 0 }}>
          <View
            style={{
              paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
              borderRadius: theme.radiusUsage.statusPill,
              borderWidth: 1, borderColor: theme.colors.statusSuccess,
              backgroundColor: theme.colors.statusSuccessSurface,
            }}
          >
            <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>{statusLabel}</AppText>
          </View>
        </View>
      </Pressable>
    </View>
  );
}

/** "Today 10:30 AM" / "12 Aug, 10:00-12:00" from the booking's real
 * preferred date and window. Returns null when neither is set, so the row
 * disappears instead of showing an empty clock. */
function formatSchedule(preferredDate: string | null, preferredTimeWindow: string | null): string | null {
  if (!preferredDate && !preferredTimeWindow) return null;
  if (!preferredDate) return preferredTimeWindow;

  const date = new Date(preferredDate);
  if (Number.isNaN(date.getTime())) return preferredTimeWindow;

  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  const dayLabel = isToday
    ? "Today"
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short" });

  return preferredTimeWindow ? `${dayLabel} ${preferredTimeWindow}` : dayLabel;
}
