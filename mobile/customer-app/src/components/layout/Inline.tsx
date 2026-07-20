import React from "react";
import { View, type ViewStyle } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SpacingKey } from "../../design-system/tokens/spacing";

export interface InlineProps {
  gap?: SpacingKey;
  align?: ViewStyle["alignItems"];
  justify?: ViewStyle["justifyContent"];
  wrap?: boolean;
  children: React.ReactNode;
  style?: ViewStyle;
}

/** Horizontal layout primitive — avoid ad hoc `marginRight` chains in screens. */
export function Inline({ gap = 4, align = "center", justify, wrap = false, children, style }: InlineProps) {
  const { theme } = useAppTheme();
  return (
    <View style={[{ flexDirection: "row", gap: theme.spacing[gap], alignItems: align, justifyContent: justify, flexWrap: wrap ? "wrap" : "nowrap" }, style]}>
      {children}
    </View>
  );
}
