import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

/** Reflects the real admin-gated workflow (spec section 3) -- never
 * "instant"/"immediate"/"guaranteed" language. */
export function DeletionWarningPanel() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start",
        padding: theme.spacing.sm, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.statusDangerSurface, borderWidth: 1, borderColor: theme.colors.statusDanger,
      }}
    >
      <Icon name="warning-outline" size="standard" color={theme.colors.statusDanger} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: theme.colors.statusDanger }}>Your account is not deleted now</AppText>
        <AppText variant="caption" color="secondary">This starts a request. You can track its status in Privacy requests.</AppText>
      </View>
    </View>
  );
}
