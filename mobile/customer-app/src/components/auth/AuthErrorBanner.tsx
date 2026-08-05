import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export function AuthErrorBanner({ message }: { message: string }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="assertive"
      style={{
        flexDirection: "row",
        alignItems: "flex-start",
        gap: theme.spacing.xs,
        padding: theme.spacing.sm,
        borderRadius: theme.radiusUsage.input,
        backgroundColor: theme.colors.statusDangerSurface,
        marginBottom: theme.spacing.base,
      }}
    >
      <Icon name="alert-circle" size="compact" color={theme.colors.statusDanger} decorative />
      <AppText variant="bodySmall" style={{ color: theme.colors.statusDanger, flex: 1 }}>{message}</AppText>
    </View>
  );
}
