import React from "react";
import { StyleSheet, ViewProps } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppSurface, type AppSurfaceVariant } from "./AppSurface";

export interface AppCardProps extends ViewProps {
  elevated?: boolean;
  variant?: AppSurfaceVariant;
}

/** Standard elevated surface: rounded corners, subtle border + shadow,
 * card padding token. Screens compose content inside this rather than
 * styling their own bordered Views. */
export function AppCard({ elevated = true, variant = "raised", style, children, ...rest }: AppCardProps) {
  const { theme } = useTheme();
  const flattened = StyleSheet.flatten(style);
  const customBackground = typeof flattened?.backgroundColor === "string" ? flattened.backgroundColor : null;
  return (
    <AppSurface
      variant={variant}
      elevated={elevated}
      colors={customBackground ? [customBackground, customBackground] : undefined}
      style={[
        {
          borderRadius: theme.radiusUsage.card,
          padding: theme.layout.cardPadding,
        },
        style,
      ]}
      {...rest}
    >
      {children}
    </AppSurface>
  );
}
