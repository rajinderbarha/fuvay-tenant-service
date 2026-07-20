import React from "react";
import { View, type ViewStyle } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SpacingKey } from "../../design-system/tokens/spacing";

export interface StackProps {
  gap?: SpacingKey;
  align?: ViewStyle["alignItems"];
  children: React.ReactNode;
  style?: ViewStyle;
}

/** Vertical layout primitive — avoid ad hoc `marginBottom` chains in screens. */
export function Stack({ gap = 4, align, children, style }: StackProps) {
  const { theme } = useAppTheme();
  return <View style={[{ flexDirection: "column", gap: theme.spacing[gap], alignItems: align }, style]}>{children}</View>;
}
