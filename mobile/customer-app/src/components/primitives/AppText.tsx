import React from "react";
import { Text, type TextProps, type TextStyle } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { TypographyVariant } from "../../design-system/tokens/typography";
import type { SemanticColors } from "../../design-system/themes/theme-types";

export interface AppTextProps extends Omit<TextProps, "style"> {
  variant?: TypographyVariant;
  color?: keyof SemanticColors;
  align?: TextStyle["textAlign"];
  selectable?: boolean;
  numberOfLines?: number;
  emphasis?: boolean;
  style?: TextStyle;
}

export function AppText({ variant = "bodyMedium", color = "textPrimary", align, selectable, numberOfLines, emphasis, style, children, ...rest }: AppTextProps) {
  const { theme } = useAppTheme();
  const typographyStyle = theme.typography[variant];

  return (
    <Text
      // allowFontScaling defaults to true (RN default) — dynamic type is never disabled.
      selectable={selectable}
      numberOfLines={numberOfLines}
      style={[typographyStyle, { color: theme.colors[color] }, emphasis ? { fontWeight: "700" } : null, align ? { textAlign: align } : null, style]}
      {...rest}
    >
      {children}
    </Text>
  );
}
