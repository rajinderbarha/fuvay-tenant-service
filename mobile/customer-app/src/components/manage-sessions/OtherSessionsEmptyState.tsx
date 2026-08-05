import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Never a security guarantee -- describes the current state honestly,
 * nothing more (spec section 8). */
export function OtherSessionsEmptyState() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.base,
        borderWidth: 1, borderStyle: "dashed", borderColor: theme.colors.borderDefault,
        borderRadius: theme.radiusUsage.card,
      }}
    >
      <Icon name="phone-portrait-outline" size="feature" color={theme.colors.textTertiary} decorative />
      <AppText variant="bodyStrong">No other active sessions</AppText>
      <AppText variant="bodySmall" color="secondary" align="center">You're only signed in on this device.</AppText>
    </View>
  );
}
