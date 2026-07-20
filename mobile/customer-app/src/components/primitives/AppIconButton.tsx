import React from "react";
import { ActivityIndicator, StyleSheet } from "react-native";
import { AppPressable } from "./AppPressable";
import { AppIcon, type IconName } from "./AppIcon";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface AppIconButtonProps {
  icon: IconName;
  accessibilityLabel: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  selected?: boolean;
  destructive?: boolean;
  testID?: string;
}

export function AppIconButton({ icon, accessibilityLabel, onPress, disabled, loading, selected, destructive, testID }: AppIconButtonProps) {
  const { theme } = useAppTheme();
  const isDisabled = disabled || loading;

  return (
    <AppPressable
      onPress={onPress}
      disabled={isDisabled}
      testID={testID}
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled: isDisabled, selected: Boolean(selected), busy: Boolean(loading) }}
      style={[
        styles.base,
        {
          borderRadius: theme.radii.full,
          backgroundColor: selected ? theme.colors.surfaceSelected : "transparent",
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={theme.colors.iconPrimary} />
      ) : (
        // Decorative here — the parent AppPressable already carries accessibilityLabel;
        // labeling both would create two accessibility elements with the same name.
        <AppIcon name={icon} color={destructive ? "iconDanger" : isDisabled ? "iconDisabled" : "iconPrimary"} />
      )}
    </AppPressable>
  );
}

const styles = StyleSheet.create({
  base: { alignItems: "center", justifyContent: "center" },
});
