import React from "react";
import { View, Image, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../index";
import { Icon } from "../Icon";
import { HomeActiveBooking } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import { distinctBadges } from "../../domain/providerBadges";

export interface MyBookingCardProps {
  booking: HomeActiveBooking;
  /** Category mascot, if one resolves from `bookableCategories` by name --
   * purely cosmetic, never changes what data is shown. */
  iconUrl?: string | null;
  onPress: () => void;
}

/**
 * One live booking: who is doing the work, their standing, and the slot they
 * committed to.
 *
 * Extracted from MyBookingSection so several can be paged side by side (see
 * MyBookingsStrip) -- the section used to own both the heading and the single
 * card, which is why only the newest booking could ever be shown.
 *
 * Every line is real backend data, and each row is omitted when its data is
 * absent rather than filled with a placeholder. Two things the reference design
 * shows are NOT rendered because nothing in this system produces them: a live
 * ETA (no arrival time is ever computed, and deriving one from an assumed travel
 * speed would be a number the app invented and the customer would plan around),
 * and a star for a technician who has not been reviewed.
 */
export function MyBookingCard({ booking, iconUrl, onPress }: MyBookingCardProps) {
  const { theme } = useTheme();

  // Same adapter the bookings list uses, so a status never reads one way here
  // and another way on the Bookings tab.
  const { statusLabel } = interpretBookingStatus(booking.status, booking.assignmentStatus ?? "");
  const title = booking.serviceName || booking.issueSummary || booking.bookingNumber || "Your booking";

  // The COMMITTED slot when there is one, falling back to what the customer
  // asked for -- never mixed, so a request is not shown as a promise.
  const scheduled = booking.scheduledDate || booking.scheduledTimeWindow;
  const scheduleLabel = scheduled
    ? formatSchedule(booking.scheduledDate, booking.scheduledTimeWindow)
    : formatSchedule(booking.preferredDate, booking.preferredTimeWindow);
  const technician = booking.technician;
  const provider = booking.provider;
  const providerName = provider?.name ?? booking.providerName ?? null;
  const providerRating = provider?.rating ?? null;
  // Deduped before slicing: two of the same label would otherwise fill both
  // slots with one claim and collide as list keys.
  const badges = distinctBadges(provider?.badges ?? []).slice(0, 2);

  return (
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
