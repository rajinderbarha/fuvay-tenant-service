import React from "react";
import { View, type ViewStyle } from "react-native";
import { AppPressable } from "./AppPressable";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export type AppCardVariant = "default" | "elevated" | "outlined" | "interactive" | "selected" | "disabled";

export interface AppCardProps {
  variant?: AppCardVariant;
  onPress?: () => void;
  accessibilityLabel?: string;
  children: React.ReactNode;
  style?: ViewStyle;
  testID?: string;
}

export function AppCard({ variant = "default", onPress, accessibilityLabel, children, style, testID }: AppCardProps) {
  const { theme } = useAppTheme();
  const isInteractive = variant === "interactive" && Boolean(onPress);
  const isDisabled = variant === "disabled";

  const cardStyle: ViewStyle = {
    backgroundColor: variant === "selected" ? theme.colors.surfaceSelected : theme.colors.surfacePrimary,
    borderRadius: theme.radii.lg,
    padding: theme.sizes.cardPadding as number,
    borderWidth: variant === "outlined" ? 1 : 0,
    borderColor: theme.colors.borderDefault,
    opacity: isDisabled ? 0.6 : 1,
    ...(variant === "elevated" ? theme.shadows.md : variant === "default" ? theme.shadows.sm : {}),
  };

  if (isInteractive) {
    return (
      <AppPressable
        onPress={onPress}
        disabled={isDisabled}
        accessibilityLabel={accessibilityLabel}
        enforceMinTouchTarget={false}
        style={[cardStyle, style]}
        testID={testID}
      >
        {children}
      </AppPressable>
    );
  }

  return (
    <View style={[cardStyle, style]} testID={testID} accessibilityLabel={accessibilityLabel}>
      {children}
    </View>
  );
}
