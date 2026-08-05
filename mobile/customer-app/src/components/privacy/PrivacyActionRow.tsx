import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

export interface PrivacyActionRowProps {
  icon: IconProps["name"];
  title: string;
  subtitle: string;
  actionLabel: string;
  onPress: () => void;
  destructive?: boolean;
  loading?: boolean;
  disabled?: boolean;
}

export function PrivacyActionRow({ icon, title, subtitle, actionLabel, onPress, destructive, loading, disabled }: PrivacyActionRowProps) {
  const { theme } = useTheme();
  const actionColor = destructive ? theme.colors.statusDanger : theme.colors.textLink;
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 36, alignItems: "center" }}>
        <Icon name={icon} size="standard" color={destructive ? theme.colors.statusDanger : theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={destructive ? { color: theme.colors.statusDanger } : undefined}>{title}</AppText>
        <AppText variant="bodySmall" color="secondary">{subtitle}</AppText>
      </View>
      <AppText
        variant="labelStrong" style={{ color: disabled ? theme.colors.textTertiary : actionColor }}
        onPress={disabled || loading ? undefined : onPress}
        accessibilityRole="button" accessibilityLabel={`${title}: ${actionLabel}`}
        accessibilityState={{ disabled: !!disabled }}
      >
        {loading ? "…" : actionLabel}
      </AppText>
    </View>
  );
}
