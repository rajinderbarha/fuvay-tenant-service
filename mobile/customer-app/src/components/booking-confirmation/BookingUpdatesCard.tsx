import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { NotificationCapability } from "../../domain/notificationCapability";

export interface BookingUpdatesCardProps {
  capability: NotificationCapability;
  /** Skip the surrounding AppCard -- see BookingActivity's `bare`, used
   * for the same reason: the design shows this row and Booking activity
   * as one continuous card. */
  bare?: boolean;
}

export function BookingUpdatesCard({ capability, bare = false }: BookingUpdatesCardProps) {
  const { theme } = useTheme();
  const content = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radius.radiusFull,
          backgroundColor: theme.colors.accentViolet, alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}
      >
        <Icon name="notifications" size="standard" color={theme.colors.textInverse} decorative />
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        {capability.kind === "enabled" ? (
          <>
            <AppText variant="body">Status updates</AppText>
            <AppText variant="caption" color="tertiary">Refresh anytime or check My Bookings</AppText>
          </>
        ) : capability.kind === "permission_not_granted" ? (
          <>
            <AppText variant="body">Get booking updates</AppText>
            <AppText variant="caption" color="tertiary">Enable notifications for status changes</AppText>
          </>
        ) : (
          <>
            <AppText variant="body">Status updates in My Bookings</AppText>
            <AppText variant="caption" color="tertiary">Notifications aren't available on this build yet</AppText>
          </>
        )}
      </View>
      {capability.kind === "enabled" ? (
        <View
          style={{
            paddingVertical: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm,
            borderRadius: theme.radiusUsage.statusPill,
            borderWidth: 1, borderColor: theme.colors.statusSuccess,
            backgroundColor: theme.colors.statusSuccessSurface,
            flexShrink: 0,
          }}
        >
          <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>Notifications on</AppText>
        </View>
      ) : capability.kind === "permission_not_granted" ? (
        <AppText variant="labelStrong" color="link">Enable</AppText>
      ) : null}
    </View>
  );
  return bare ? content : <AppCard>{content}</AppCard>;
}
