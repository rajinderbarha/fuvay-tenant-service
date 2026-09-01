import React from "react";
import { LinearGradient } from "expo-linear-gradient";
import type { ColorValue, StyleProp, ViewProps, ViewStyle } from "react-native";

import { useTheme } from "../design-system/theme";

export type AppSurfaceVariant = "raised" | "interactive" | "inset" | "flat";

export interface AppSurfaceProps extends Omit<ViewProps, "style"> {
  children?: React.ReactNode;
  variant?: AppSurfaceVariant;
  style?: StyleProp<ViewStyle>;
  colors?: readonly [ColorValue, ColorValue, ...ColorValue[]];
  elevated?: boolean;
}

/**
 * Canonical layered surface. Cards, icon wells and navigation shells all
 * consume this primitive so light/dark depth does not drift by screen.
 */
export function AppSurface({
  children,
  variant = "raised",
  style,
  colors,
  elevated = variant === "raised" || variant === "interactive",
  ...rest
}: AppSurfaceProps) {
  const { theme } = useTheme();
  const recipe = variant === "raised"
    ? theme.material.raised
    : variant === "interactive"
      ? theme.material.interactive
      : variant === "inset"
        ? theme.material.inset
        : [theme.colors.surfaceDefault, theme.colors.surfaceDefault] as const;

  return (
    <LinearGradient
      colors={(colors ?? recipe) as [ColorValue, ColorValue, ...ColorValue[]]}
      start={{ x: 0.5, y: 0 }}
      end={{ x: 0.5, y: 1 }}
      {...rest}
      style={[
        {
          borderWidth: 1,
          borderColor: variant === "inset" ? theme.material.outlineStrong : theme.material.outline,
          borderRadius: theme.radiusUsage.card,
        },
        elevated ? theme.shadow.md : null,
        style,
      ]}
    >
      {children}
    </LinearGradient>
  );
}
