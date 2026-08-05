import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { NotificationCapability } from "../../domain/notificationCapability";

export function BookingUpdatesCard({ capability }: { capability: NotificationCapability }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <Icon name="notifications-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <View style={{ flex: 1 }}>
          {capability.kind === "enabled" ? (
            <>
              <AppText variant="body">We'll send status updates</AppText>
              <AppText variant="caption" color="tertiary">Provider assignment and visit scheduling</AppText>
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
        <AppText variant="labelStrong" color={capability.kind === "enabled" ? "success" : "secondary"}>
          {capability.kind === "enabled" ? "On" : capability.kind === "permission_not_granted" ? "Enable" : ""}
        </AppText>
      </View>
    </AppCard>
  );
}
