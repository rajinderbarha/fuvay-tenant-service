import React from "react";
import { Pressable } from "react-native";
import { useTheme } from "../design-system/theme";
import { Icon, IconProps } from "./Icon";
import { AppSurface } from "./AppSurface";

export interface AppIconButtonProps {
  name: IconProps["name"];
  onPress: () => void;
  accessibilityLabel: string;
  disabled?: boolean;
  tone?: "default" | "primary";
}

/** Icon-only button. accessibilityLabel is required (not optional) since
 * an icon alone never conveys its action to a screen reader. */
export function AppIconButton({ name, onPress, accessibilityLabel, disabled, tone = "default" }: AppIconButtonProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled: !!disabled }}
      hitSlop={8}
      style={({ pressed }) => ({
        width: theme.touchTargets.iconButton,
        height: theme.touchTargets.iconButton,
        alignItems: "center",
        justifyContent: "center",
        opacity: disabled ? theme.opacity.disabled : 1,
        transform: [{ scale: pressed ? 0.96 : 1 }],
      })}
    >
      <AppSurface
        variant="interactive"
        style={{
          width: theme.touchTargets.iconButton,
          height: theme.touchTargets.iconButton,
          borderRadius: theme.radius.radiusFull,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Icon name={name} size="navigation" color={tone === "primary" ? theme.colors.brandPrimaryStrong : theme.colors.textPrimary} />
      </AppSurface>
    </Pressable>
  );
}
