import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { AppIconButton } from "./AppIconButton";
import { IconProps } from "./Icon";

export interface AppHeaderProps {
  title: string;
  onBack?: () => void;
  rightIcon?: IconProps["name"];
  onRightPress?: () => void;
  rightAccessibilityLabel?: string;
}

/** Screen header: optional back action, title, optional single right
 * action. Keeps header layout consistent app-wide instead of ad hoc rows
 * per screen. */
export function AppHeader({ title, onBack, rightIcon, onRightPress, rightAccessibilityLabel }: AppHeaderProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        minHeight: theme.touchTargets.comfortable,
        gap: theme.spacing.sm,
      }}
    >
      {onBack ? (
        <AppIconButton name="chevron-back" onPress={onBack} accessibilityLabel="Go back" />
      ) : null}
      <AppText variant="headingSmall" style={{ flex: 1 }} numberOfLines={1}>
        {title}
      </AppText>
      {rightIcon && onRightPress ? (
        <AppIconButton name={rightIcon} onPress={onRightPress} accessibilityLabel={rightAccessibilityLabel ?? "Action"} />
      ) : null}
    </View>
  );
}
