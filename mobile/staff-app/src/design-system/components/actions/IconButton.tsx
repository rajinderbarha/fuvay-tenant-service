import React from "react";
import { Pressable, ActivityIndicator, ViewStyle } from "react-native";
import { useTheme } from "../../themes";
import { Icon, IconProps } from "../Icon";
import { layout } from "../../tokens/spacing";

export interface IconButtonProps {
  icon: IconProps["name"];
  /** Required -- an icon-only button with no adjacent text MUST have an
   * accessible name (spec requirement). */
  accessibilityLabel: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  tone?: "default" | "danger";
  style?: ViewStyle;
}

/** Circular icon-only touch target, minimum 44-48px regardless of the icon's
 * own size token. */
export function IconButton({ icon, accessibilityLabel, onPress, disabled, loading, tone = "default", style }: IconButtonProps) {
  const { theme } = useTheme();
  const isDisabled = disabled || loading;
  const color = tone === "danger" ? theme.colors.statusDanger : theme.colors.textPrimary;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      hitSlop={8}
      style={({ pressed }) => [
        {
          width: layout.minTouchTarget,
          height: layout.minTouchTarget,
          borderRadius: theme.radiusUsage.avatar,
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: pressed ? theme.colors.surfaceInteractive : "transparent",
          opacity: isDisabled ? theme.opacity.disabled : 1,
        },
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={color} /> : <Icon name={icon} size="navigation" color={color} decorative />}
    </Pressable>
  );
}
