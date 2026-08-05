import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

export interface DeletionInfoRowProps {
  icon: IconProps["name"];
  title: string;
  subtitle: string;
}

export function DeletionInfoRow({ icon, title, subtitle }: DeletionInfoRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 32, alignItems: "center" }}>
        <Icon name={icon} size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{title}</AppText>
        <AppText variant="bodySmall" color="secondary">{subtitle}</AppText>
      </View>
    </View>
  );
}
