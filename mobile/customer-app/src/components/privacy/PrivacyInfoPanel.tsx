import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Product guidance only -- never a compliance guarantee, instant-delete
 * claim, or export-time promise (spec section 5). */
export function PrivacyInfoPanel() {
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
        <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Your data, your choices</AppText>
        <AppText variant="caption" color="secondary">Access your information and manage privacy requests.</AppText>
      </View>
    </View>
  );
}
