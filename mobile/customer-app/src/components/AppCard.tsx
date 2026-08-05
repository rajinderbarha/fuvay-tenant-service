import React from "react";
import { View, ViewProps } from "react-native";
import { useTheme } from "../design-system/theme";

export interface AppCardProps extends ViewProps {
  elevated?: boolean;
}

/** Standard elevated surface: rounded corners, subtle border + shadow,
 * card padding token. Screens compose content inside this rather than
 * styling their own bordered Views. */
export function AppCard({ elevated = true, style, children, ...rest }: AppCardProps) {
  const { theme } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: theme.colors.surfaceDefault,
          borderRadius: theme.radiusUsage.card,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.layout.cardPadding,
        },
        elevated ? theme.shadow.sm : null,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}
