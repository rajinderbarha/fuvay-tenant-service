import React from "react";
import { View } from "react-native";
import { AppText } from "../primitives/AppText";
import { AppIcon } from "../primitives/AppIcon";
import { useConnectivity } from "../../hooks/useConnectivity";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

/** Renders nothing when online or when status is not yet known — never blocks the app. */
export function OfflineBanner() {
  const { theme } = useAppTheme();
  const { status } = useConnectivity();

  if (status !== "offline") return null;

  return (
    <View
      accessible
      accessibilityRole="alert"
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing[3],
        backgroundColor: theme.colors.statusWarningBackground,
        paddingVertical: theme.spacing[3],
        paddingHorizontal: theme.spacing[6],
      }}
    >
      <AppIcon name="cloud-offline" size="sm" color="iconWarning" />
      <AppText variant="labelMedium" style={{ color: theme.colors.statusWarningForeground }}>
        You're offline
      </AppText>
    </View>
  );
}
