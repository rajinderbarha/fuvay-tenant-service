import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";

export function FieldLabel({ label, required }: { label: string; required?: boolean }) {
  const { theme } = useTheme();
  return (
    <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>
      {label}{required ? " *" : ""}
    </AppText>
  );
}

export function FieldHelper({ text }: { text?: string }) {
  const { theme } = useTheme();
  if (!text) return null;
  return (
    <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
      {text}
    </AppText>
  );
}

/** FormError -- accessible error announcement. `accessibilityLiveRegion`
 * ensures screen readers announce validation errors as they appear. */
export function FormError({ message }: { message?: string }) {
  const { theme } = useTheme();
  if (!message) return null;
  return (
    <View accessibilityLiveRegion="polite" accessibilityRole="alert">
      <AppText variant="caption" color="danger" style={{ marginTop: theme.spacing.xxs }}>
        {message}
      </AppText>
    </View>
  );
}

/** Shared border/background resolution for input-shaped controls, so
 * TextField/TextArea/SelectField/CurrencyField/QuantityField all react to
 * error/disabled/focus state identically. */
export function useFieldChrome(opts: { error?: boolean; disabled?: boolean; focused?: boolean }) {
  const { theme } = useTheme();
  const { colors, radiusUsage } = theme;
  let borderColor = colors.borderDefault;
  if (opts.disabled) borderColor = colors.borderDisabled;
  else if (opts.error) borderColor = colors.statusDanger;
  else if (opts.focused) borderColor = colors.borderFocus;

  return {
    borderColor,
    backgroundColor: opts.disabled ? colors.surfaceDisabled : colors.surfaceDefault,
    borderRadius: radiusUsage.input,
    borderWidth: opts.focused || opts.error ? 2 : 1,
  };
}
