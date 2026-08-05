import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export function PrivacyRequestsEmptyState() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.base,
        borderWidth: 1, borderStyle: "dashed", borderColor: theme.colors.borderDefault,
        borderRadius: theme.radiusUsage.card,
      }}
    >
      <Icon name="clipboard-outline" size="feature" color={theme.colors.textTertiary} decorative />
      <AppText variant="bodyStrong">No active requests</AppText>
      <AppText variant="bodySmall" color="secondary" align="center">Your export and deletion requests will appear here.</AppText>
    </View>
  );
}
