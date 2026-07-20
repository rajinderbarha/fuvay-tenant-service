import React from "react";
import { View } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SemanticColors } from "../../design-system/themes/theme-types";

export interface AppDividerProps {
  orientation?: "horizontal" | "vertical";
  inset?: boolean;
  color?: keyof Pick<SemanticColors, "borderSubtle" | "borderDefault" | "borderStrong">;
}

export function AppDivider({ orientation = "horizontal", inset = false, color = "borderSubtle" }: AppDividerProps) {
  const { theme } = useAppTheme();
  const thickness = 1;
  const insetAmount = inset ? theme.spacing[6] : 0;

  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={
        orientation === "horizontal"
          ? { height: thickness, backgroundColor: theme.colors[color], marginLeft: insetAmount }
          : { width: thickness, backgroundColor: theme.colors[color], marginTop: insetAmount, alignSelf: "stretch" }
      }
    />
  );
}
