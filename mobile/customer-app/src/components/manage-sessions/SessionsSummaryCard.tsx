import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface SessionsSummaryCardProps {
  /** The full active-session count from the backend response's own
   * `total` -- never derived from a single paginated page (spec section
   * 5). */
  activeCount: number;
}

export function SessionsSummaryCard({ activeCount }: SessionsSummaryCardProps) {
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
        <AppText variant="bodyStrong" style={{ color: theme.colors.brandPrimaryStrong }}>
          {activeCount} active session{activeCount === 1 ? "" : "s"}
        </AppText>
        <AppText variant="caption" color="secondary">Sign out any device you don't recognize.</AppText>
      </View>
    </View>
  );
}
