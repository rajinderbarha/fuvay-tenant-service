import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

export interface TrustBenefitCardProps {
  label: string;
  icon: IconProps["name"];
}

/** Static marketing copy, not backend data -- see homeViewModels.ts. */
export function TrustBenefitCard({ label, icon }: TrustBenefitCardProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flex: 1, alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.sm,
        borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name={icon} size="navigation" color={theme.colors.brandPrimaryStrong} decorative />
      <AppText variant="caption" align="center" numberOfLines={2}>{label}</AppText>
    </View>
  );
}
