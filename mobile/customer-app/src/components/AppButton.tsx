import React, { useState } from "react";
import { Pressable, ActivityIndicator, ViewStyle, GestureResponderEvent } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";

export type ButtonTone = "primary" | "secondary" | "tertiary" | "destructive";
export type ButtonSize = "default" | "compact";

export interface AppButtonProps {
  label: string;
  onPress: () => void | Promise<void>;
  tone?: ButtonTone;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  /** Shown when disabled due to a rule the customer should understand --
   * disabled actions must explain why, not just look faded. */
  disabledReason?: string;
  fullWidth?: boolean;
  leadingIcon?: React.ReactNode;
  accessibilityLabel?: string;
  style?: ViewStyle;
}

function toneColors(theme: ReturnType<typeof useTheme>["theme"], tone: ButtonTone, pressed: boolean, disabled: boolean) {
  const { colors } = theme;
  if (disabled) {
    return { bg: colors.surfaceDisabled, fg: colors.textDisabled, border: colors.borderDisabled };
  }
  switch (tone) {
    case "primary":
      return { bg: pressed ? colors.brandPrimaryPressed : colors.brandPrimary, fg: colors.brandOnPrimary, border: "transparent" };
    case "secondary":
      return { bg: pressed ? colors.surfaceSelected : colors.surfaceInteractive, fg: colors.textPrimary, border: colors.borderDefault };
    case "tertiary":
      return { bg: pressed ? colors.surfaceInteractive : "transparent", fg: colors.textPrimary, border: "transparent" };
    case "destructive":
      return { bg: pressed ? colors.statusDangerSurface : "transparent", fg: colors.statusDanger, border: colors.statusDanger };
  }
}

/**
 * Primary/secondary/tertiary/destructive button in one component (tone
 * prop) mirroring the Staff App button language. Fixed-height layout
 * (loading swaps the label for a same-size spinner, never shrinks), and an
 * internal busy guard blocks a second tap while an async onPress runs --
 * this alone prevents most double-submit bugs at the source.
 */
export function AppButton({
  label, onPress, tone = "primary", size = "default", disabled = false, loading = false,
  disabledReason, fullWidth = false, leadingIcon, accessibilityLabel, style,
}: AppButtonProps) {
  const { theme } = useTheme();
  const [busy, setBusy] = useState(false);
  const isLoading = loading || busy;
  const isDisabled = disabled || isLoading;

  async function handlePress(_e: GestureResponderEvent) {
    if (isDisabled) return;
    const result = onPress();
    if (result && typeof (result as Promise<void>).then === "function") {
      setBusy(true);
      try {
        await result;
      } finally {
        setBusy(false);
      }
    }
  }

  return (
    <>
      <Pressable
        onPress={handlePress}
        disabled={isDisabled}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? label}
        accessibilityState={{ disabled: isDisabled, busy: isLoading }}
        hitSlop={8}
        style={({ pressed }) => {
          const c = toneColors(theme, tone, pressed, disabled && !isLoading);
          return [
            {
              minHeight: theme.touchTargets.minimum,
              paddingHorizontal: theme.spacing.base,
              borderRadius: theme.radiusUsage.button,
              backgroundColor: c.bg,
              borderWidth: tone === "secondary" || tone === "destructive" ? 1 : 0,
              borderColor: c.border,
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              gap: theme.spacing.xs,
              opacity: disabled && !isLoading ? theme.opacity.disabled : 1,
              alignSelf: fullWidth ? "stretch" : "flex-start",
              width: fullWidth ? "100%" : undefined,
            },
            size === "compact" ? { minHeight: 40, paddingHorizontal: theme.spacing.sm } : null,
            style,
          ];
        }}
      >
        {({ pressed }) => {
          const c = toneColors(theme, tone, pressed, disabled && !isLoading);
          return isLoading ? (
            <ActivityIndicator color={c.fg} />
          ) : (
            <>
              {leadingIcon}
              <AppText variant="button" style={{ color: c.fg }}>{label}</AppText>
            </>
          );
        }}
      </Pressable>
      {disabled && disabledReason ? (
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
          {disabledReason}
        </AppText>
      ) : null}
    </>
  );
}
