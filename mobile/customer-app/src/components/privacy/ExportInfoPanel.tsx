import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export function ExportInfoPanel() {
  const { theme } = useTheme();
  return (
    <AppCard
      style={{
        gap: theme.spacing.xs, backgroundColor: theme.colors.statusWarningSurface,
        borderColor: theme.colors.statusWarning, borderWidth: 1,
      }}
    >
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <Icon name="shield-checkmark-outline" size="feature" color={theme.colors.statusWarning} decorative />
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong">Your Fuvay data, securely prepared</AppText>
          <AppText variant="bodySmall" color="secondary">Request a copy of the information linked to your account.</AppText>
          <View
            style={{
              flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, alignSelf: "flex-start",
              marginTop: theme.spacing.xxs, paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xxs,
              borderRadius: theme.radiusUsage.statusPill, borderWidth: 1, borderColor: theme.colors.borderDefault,
            }}
          >
            <Icon name="lock-closed-outline" size="compact" color={theme.colors.textSecondary} decorative />
            <AppText variant="caption" color="secondary">Private & secure</AppText>
          </View>
        </View>
      </View>
    </AppCard>
  );
}
