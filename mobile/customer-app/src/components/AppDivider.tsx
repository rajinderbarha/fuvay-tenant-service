import React from "react";
import { View, ViewProps } from "react-native";
import { useTheme } from "../design-system/theme";

export function AppDivider({ style, ...rest }: ViewProps) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityElementsHidden
      style={[{ height: 1, backgroundColor: theme.colors.borderSubtle }, style]}
      {...rest}
    />
  );
}
