import React, { useState } from "react";
import { Pressable, ActivityIndicator, ViewStyle, GestureResponderEvent } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { layout } from "../../tokens/spacing";

export type ButtonTone = "primary" | "secondary" | "tertiary" | "destructive";
export type ButtonSize = "default" | "compact";

export interface BaseButtonProps {
  label: string;
  onPress: () => void | Promise<void>;
  tone?: ButtonTone;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  /** Shown when disabled due to workflow policy -- disabled actions must
   * explain why, not just look faded (spec requirement). */
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
 * Shared button behavior: fixed-height layout (loading never changes
 * width/height -- the label is swapped for a same-size spinner, not
 * removed), double-submission guard (internal `busy` state blocks a second
 * tap while an async onPress is in flight), and a required disabled-reason
 * caption when disabled.
 */
export function BaseButton({
  label, onPress, tone = "primary", size = "default", disabled = false, loading = false,
  disabledReason, fullWidth = false, leadingIcon, accessibilityLabel, style,
}: BaseButtonProps) {
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
              minHeight: layout.minTouchTarget,
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
