import React from "react";
import { ActivityIndicator, View } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export type LoadingIndicatorVariant = "inline" | "screen" | "button" | "section";

export interface LoadingIndicatorProps {
  variant?: LoadingIndicatorVariant;
  label?: string;
}

export function LoadingIndicator({ variant = "inline", label = "Loading" }: LoadingIndicatorProps) {
  const { theme } = useAppTheme();
  const size = variant === "screen" || variant === "section" ? "large" : "small";

  const content = <ActivityIndicator size={size} color={theme.colors.actionPrimary} accessibilityLabel={label} />;

  if (variant === "screen") {
    return (
      <View
        accessible
        style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.backgroundPrimary }}
        accessibilityRole="progressbar"
      >
        {content}
      </View>
    );
  }

  if (variant === "section") {
    return (
      <View accessible style={{ paddingVertical: theme.spacing[9], alignItems: "center" }} accessibilityRole="progressbar">
        {content}
      </View>
    );
  }

  return content;
}
