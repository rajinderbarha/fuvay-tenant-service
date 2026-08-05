import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Guidance only -- never a security score or "your account is safe"
 * claim (spec section 7). */
export function LoginActivitySummaryPanel() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start",
        padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.brandPrimaryMuted, borderWidth: 1, borderColor: theme.colors.brandPrimary,
      }}
    >
      <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Your recent sign-ins</AppText>
        <AppText variant="caption" color="secondary">Check for activity you don't recognize.</AppText>
      </View>
    </View>
  );
}
