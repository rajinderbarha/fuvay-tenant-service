import React from "react";
import { Text, TextProps } from "react-native";
import { useTheme } from "../../themes";
import { TypographyToken } from "../../tokens/typography";

export type TextColorRole = "primary" | "secondary" | "tertiary" | "disabled" | "inverse" | "link"
  | "success" | "warning" | "danger" | "info";

export interface AppTextProps extends TextProps {
  variant?: TypographyToken;
  color?: TextColorRole;
  align?: "auto" | "left" | "right" | "center" | "justify";
}

const COLOR_ROLE_KEY: Record<TextColorRole, string> = {
  primary: "textPrimary", secondary: "textSecondary", tertiary: "textTertiary",
  disabled: "textDisabled", inverse: "textInverse", link: "textLink",
  success: "statusSuccess", warning: "statusWarning", danger: "statusDanger", info: "statusInfo",
};

/**
 * Base text primitive -- named AppText (not `Text`) to avoid confusing
 * collisions with React Native's own `Text`. Font scaling is intentionally
 * left ENABLED (allowFontScaling defaults true) -- never globally disable
 * OS accessibility font scaling.
 */
export function AppText({ variant = "body", color = "primary", align, style, ...rest }: AppTextProps) {
  const { theme } = useTheme();
  const colorValue = (theme.colors as unknown as Record<string, string>)[COLOR_ROLE_KEY[color]];
  return (
    <Text
      style={[theme.typography[variant], { color: colorValue }, align ? { textAlign: align } : null, style]}
      {...rest}
    />
  );
}
