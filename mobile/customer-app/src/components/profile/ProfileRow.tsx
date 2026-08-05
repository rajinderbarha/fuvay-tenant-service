import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";

export interface ProfileRowProps {
  icon: IconProps["name"];
  label: string;
  subtitle?: string;
  onPress?: () => void;
  trailing?: React.ReactNode;
  external?: boolean;
  destructive?: boolean;
  bordered?: boolean;
}

export function ProfileRow({ icon, label, subtitle, onPress, trailing, external, destructive, bordered = true }: ProfileRowProps) {
  const { theme } = useTheme();
  const content = (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.base,
        minHeight: theme.touchTargets.comfortable,
        borderBottomWidth: bordered ? 1 : 0, borderBottomColor: theme.colors.borderSubtle,
      }}
    >
      <Icon name={icon} size="standard" color={destructive ? theme.colors.statusDanger : theme.colors.textSecondary} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="body" color={destructive ? "danger" : "primary"}>{label}</AppText>
        {subtitle ? <AppText variant="caption" color="tertiary">{subtitle}</AppText> : null}
      </View>
      {trailing}
      {onPress ? (
        <Icon name={external ? "open-outline" : "chevron-forward"} size="compact" color={theme.colors.iconDefault} decorative />
      ) : null}
    </View>
  );

  if (!onPress) return content;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${label}. ${subtitle}` : label}
      accessibilityHint={external ? "Opens outside the app" : undefined}
    >
      {content}
    </Pressable>
  );
}
