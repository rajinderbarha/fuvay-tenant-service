import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/**
 * CLOSURE (2026-08-01): the notification bell was removed -- an icon
 * with no real destination is a dead control and an accessibility trap
 * (spec closure item 3). It returns once Notifications has a real
 * customer route to navigate to; until then, this header shows title
 * copy only.
 */
export interface BookingsHeaderProps {
  activeCount?: number;
  completedCount?: number;
  onSearch?: () => void;
}

/** Scan-first heading for the booking workspace. The compact summary uses
 * authoritative backend counts and keeps search visible without competing
 * with the status tabs. */
export function BookingsHeader({ activeCount, completedCount, onSearch }: BookingsHeaderProps) {
  const { theme } = useTheme();
  const hasCounts = activeCount !== undefined && completedCount !== undefined;

  return (
    <View style={{ gap: theme.spacing.md }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.md }}>
        <View style={{ flex: 1 }}>
          <AppText variant="headingLarge" accessibilityRole="header">My bookings</AppText>
          <AppText variant="bodySmall" color="secondary">Track visits, approvals and completed work</AppText>
        </View>
        {onSearch ? (
          <Pressable
            onPress={onSearch}
            accessibilityRole="button"
            accessibilityLabel="Search and filter bookings"
            hitSlop={8}
            style={({ pressed }) => ({
              width: theme.touchTargets.minimum,
              height: theme.touchTargets.minimum,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.surfaceDefault,
              borderWidth: 1,
              borderColor: theme.colors.borderSubtle,
              opacity: pressed ? 0.72 : 1,
              ...theme.shadow.sm,
            })}
          >
            <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
          </Pressable>
        ) : null}
      </View>

      {hasCounts ? (
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            paddingHorizontal: theme.spacing.base,
            paddingVertical: theme.spacing.md,
            borderRadius: theme.radiusUsage.card,
            backgroundColor: theme.colors.brandPrimaryMuted,
            borderWidth: 1,
            borderColor: theme.colors.borderFocus,
          }}
        >
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimary,
              alignItems: "center",
              justifyContent: "center",
              marginRight: theme.spacing.md,
            }}
          >
            <Icon name="calendar-outline" size="standard" color={theme.colors.brandOnPrimary} decorative />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">
              {activeCount === 1 ? "1 active request" : `${activeCount} active requests`}
            </AppText>
            <AppText variant="caption" color="secondary">
              {completedCount === 1 ? "1 completed service" : `${completedCount} completed services`}
            </AppText>
          </View>
          <View style={{ alignItems: "flex-end" }}>
            <AppText variant="caption" color="secondary">Total</AppText>
            <AppText variant="headingSmall" style={{ color: theme.colors.brandPrimaryStrong }}>
              {activeCount + completedCount}
            </AppText>
          </View>
        </View>
      ) : null}
    </View>
  );
}
