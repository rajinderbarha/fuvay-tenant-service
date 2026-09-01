import React, { useState } from "react";
import { Pressable, ActivityIndicator, ViewStyle, GestureResponderEvent } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { AppSurface } from "./AppSurface";

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
  /** Rendered after the label, e.g. a forward arrow on a "continue"-style
   * action. Like `leadingIcon`, it is hidden while loading so the button
   * never shows a spinner and an icon at once. */
  trailingIcon?: React.ReactNode;
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
  disabledReason, fullWidth = false, leadingIcon, trailingIcon, accessibilityLabel, style,
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
          return [
            {
              opacity: disabled && !isLoading ? theme.opacity.disabled : 1,
              alignSelf: fullWidth ? "stretch" : "flex-start",
              width: fullWidth ? "100%" : undefined,
              transform: [{ scale: pressed ? 0.985 : 1 }],
            },
            style,
          ];
        }}
      >
        {({ pressed }) => {
          const c = toneColors(theme, tone, pressed, disabled && !isLoading);
          const gradient = tone === "primary"
            ? [pressed ? theme.colors.brandPrimaryPressed : theme.colors.brandPrimary, theme.colors.brandPrimaryPressed] as const
            : [c.bg, c.bg] as const;
          return (
            <AppSurface
              variant={tone === "secondary" ? "interactive" : "flat"}
              elevated={tone === "primary" || tone === "secondary"}
              colors={gradient}
              style={{
                minHeight: size === "compact" ? 40 : theme.touchTargets.minimum,
                paddingHorizontal: size === "compact" ? theme.spacing.sm : theme.spacing.base,
                borderRadius: theme.radiusUsage.button,
                borderWidth: tone === "secondary" || tone === "destructive" ? 1 : 0,
                borderColor: c.border,
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
                gap: theme.spacing.xs,
              }}
            >
              {isLoading ? (
                <ActivityIndicator color={c.fg} />
              ) : (
                <>
                  {leadingIcon}
                  <AppText variant="button" style={{ color: c.fg }}>{label}</AppText>
                  {trailingIcon}
                </>
              )}
            </AppSurface>
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
