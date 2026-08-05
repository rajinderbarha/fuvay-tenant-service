import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { Icon } from "./Icon";
import { useNetworkStatus } from "../hooks/useNetworkStatus";

/** Persistent top banner shown whenever the device is offline or the
 * network is unreachable. Purely informational -- it never blocks
 * navigation, and it never implies an action completed while offline. */
export function OfflineBanner() {
  const { theme } = useTheme();
  const status = useNetworkStatus();
  const isOffline = status === "offline" || status === "internet_reachable_false";

  if (!isOffline) return null;

  return (
    <View
      accessibilityLiveRegion="polite"
      accessibilityRole="alert"
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.xs,
        paddingVertical: theme.spacing.xs,
        paddingHorizontal: theme.spacing.base,
        backgroundColor: theme.colors.statusWarningSurface,
      }}
    >
      <Icon name="cloud-offline-outline" size="compact" color={theme.colors.statusWarning} decorative />
      <AppText variant="caption" style={{ color: theme.colors.statusWarning }}>
        You're offline. Some information may be out of date.
      </AppText>
    </View>
  );
}
