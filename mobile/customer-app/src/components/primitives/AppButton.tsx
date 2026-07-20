import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { AppPressable } from "./AppPressable";
import { AppText } from "./AppText";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export type AppButtonVariant = "primary" | "secondary" | "tertiary" | "destructive" | "text" | "icon-only";
export type AppButtonSize = "small" | "medium" | "large";

export interface AppButtonProps {
  label: string;
  onPress: () => void;
  variant?: AppButtonVariant;
  size?: AppButtonSize;
  disabled?: boolean;
  loading?: boolean;
  /** Required accessibility label when variant is "icon-only" and `label` is not visually rendered. */
  accessibilityLabel?: string;
  icon?: React.ReactNode;
  testID?: string;
}

const HEIGHT: Record<AppButtonSize, number> = { small: 36, medium: 44, large: 52 };
const HPAD: Record<AppButtonSize, number> = { small: 12, medium: 16, large: 20 };

export function AppButton({
  label,
  onPress,
  variant = "primary",
  size = "medium",
  disabled = false,
  loading = false,
  accessibilityLabel,
  icon,
  testID,
}: AppButtonProps) {
  const { theme } = useAppTheme();
  const isDisabled = disabled || loading;

  const { backgroundColor, textColor, borderColor } = resolveColors(variant, theme, isDisabled);

  return (
    <AppPressable
      onPress={onPress}
      disabled={isDisabled}
      testID={testID}
      accessibilityLabel={variant === "icon-only" ? (accessibilityLabel ?? label) : accessibilityLabel}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      enforceMinTouchTarget
      style={[
        styles.base,
        {
          height: HEIGHT[size],
          paddingHorizontal: variant === "icon-only" ? 0 : HPAD[size],
          width: variant === "icon-only" ? HEIGHT[size] : undefined,
          backgroundColor,
          borderColor,
          borderWidth: variant === "secondary" ? 1 : 0,
          borderRadius: theme.radii.md,
        },
      ]}
    >
      {/* Loading state swaps content for a spinner without changing button dimensions. */}
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator size="small" color={textColor} />
        ) : (
          <>
            {icon}
            {variant !== "icon-only" ? (
              <AppText variant="labelLarge" style={{ color: textColor }}>
                {label}
              </AppText>
            ) : null}
          </>
        )}
      </View>
    </AppPressable>
  );
}

function resolveColors(variant: AppButtonVariant, theme: ReturnType<typeof useAppTheme>["theme"], isDisabled: boolean) {
  if (isDisabled) {
    return {
      backgroundColor: variant === "text" || variant === "icon-only" ? "transparent" : theme.colors.actionPrimaryDisabled,
      textColor: theme.colors.textDisabled,
      borderColor: theme.colors.borderSubtle,
    };
  }
  switch (variant) {
    case "primary":
      return { backgroundColor: theme.colors.actionPrimary, textColor: theme.colors.textInverse, borderColor: "transparent" };
    case "secondary":
      return { backgroundColor: theme.colors.actionSecondary, textColor: theme.colors.textPrimary, borderColor: theme.colors.borderDefault };
    case "tertiary":
      return { backgroundColor: "transparent", textColor: theme.colors.textLink, borderColor: "transparent" };
    case "destructive":
      return { backgroundColor: theme.colors.actionDestructive, textColor: theme.colors.textInverse, borderColor: "transparent" };
    case "text":
    case "icon-only":
      return { backgroundColor: "transparent", textColor: theme.colors.textPrimary, borderColor: "transparent" };
  }
}

const styles = StyleSheet.create({
  base: { alignItems: "center", justifyContent: "center" },
  content: { flexDirection: "row", alignItems: "center", gap: 8 },
});
