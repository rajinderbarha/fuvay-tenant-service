import React from "react";
import { View, Image, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../index";
import { Icon } from "../Icon";
import { HomeActiveBooking } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import { standingBadge } from "../../domain/providerBadges";
import { resolveBadgeIcon } from "../../domain/badgeIcon";

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
  const { statusLabel, stage } = interpretBookingStatus(booking.status, booking.assignmentStatus ?? "");
  // A pill painted success-green whatever the status told the customer everything was
  // fine, including on a cancelled booking. Tone follows the real stage; anything the
  // adapter cannot place reads neutral rather than reassuring.
  const statusTone = stage === "scheduled"
    ? { text: theme.colors.statusSuccess, surface: theme.colors.statusSuccessSurface }
    : stage === "unknown"
    ? { text: theme.colors.textSecondary, surface: theme.colors.surfaceSecondary }
    : { text: theme.colors.statusInfo, surface: theme.colors.statusInfoSurface };
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
  // ONE badge: the provider's earned standing. Independent badges are shown on the
  // fuller provider surfaces, not here -- a row of pills on a card this size is what
  // made it unreadable, and a customer reads several pills as several endorsements.
  const standing = standingBadge(provider?.badges ?? []);

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

        <View style={{ flex: 1, minWidth: 0, gap: theme.spacing.xs }}>
          {/* Title and status share the top line. They used to sit in separate
              columns, which squeezed the title into a narrow strip and pushed
              everything else into its own cramped row. */}
          <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.xs }}>
            <AppText variant="bodyStrong" numberOfLines={1} style={{ flex: 1 }}>{title}</AppText>
            <View
              style={{
                paddingVertical: 2, paddingHorizontal: theme.spacing.xs,
                borderRadius: theme.radiusUsage.statusPill,
                backgroundColor: statusTone.surface,
                flexShrink: 0,
              }}
            >
              <AppText variant="caption" style={{ color: statusTone.text }}>{statusLabel}</AppText>
            </View>
          </View>

          {/* One line for WHO, one for WHEN. The previous version stacked provider,
              rating, technician, a badge row and the slot as five separate rows in a
              52pt-tall card, which is what made it unreadable. */}
          {providerName ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
              <AppText variant="caption" color="secondary" numberOfLines={1} style={{ flexShrink: 1 }}>
                {providerName}
              </AppText>
              {provider?.verified ? (
                <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimary} decorative />
              ) : null}
              {providerRating != null ? (
                <>
                  <Icon name="star" size="compact" color={theme.colors.statusWarning} decorative />
                  <AppText variant="caption" color="secondary">{providerRating.toFixed(1)}</AppText>
                </>
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

          {/* Standing and slot share the last line: each is short, and giving them a
              row apiece is what turned four facts into a wall. Either side is omitted
              when there is nothing real to put there. */}
          {standing || scheduleLabel ? (
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: theme.spacing.xs }}>
              {standing ? (
                <View
                  style={{
                    flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
                    paddingVertical: 2, paddingHorizontal: theme.spacing.xs,
                    borderRadius: theme.radiusUsage.statusPill,
                    backgroundColor: theme.colors.surfaceInteractive,
                    flexShrink: 1,
                  }}
                >
                  {/* WITH its icon -- which never rendered before, because badge icon
                      names ("shield-check", "crown") are not Ionicons names and an
                      unknown name draws nothing at all. */}
                  <Icon
                    name={resolveBadgeIcon(standing.icon)}
                    size="compact"
                    color={standing.color ?? theme.colors.brandPrimaryStrong}
                    decorative
                  />
                  <AppText
                    variant="caption"
                    numberOfLines={1}
                    style={{ color: standing.color ?? theme.colors.textLink }}
                  >
                    {standing.name}
                  </AppText>
                </View>
              ) : <View />}

              {scheduleLabel ? (
                <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, flexShrink: 0 }}>
                  <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
                  <AppText variant="caption" color="secondary" numberOfLines={1}>{scheduleLabel}</AppText>
                </View>
              ) : null}
            </View>
          ) : null}
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
