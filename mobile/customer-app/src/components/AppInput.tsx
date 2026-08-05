import React, { useState } from "react";
import { TextInput, TextInputProps, View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";

export interface AppInputProps extends TextInputProps {
  label?: string;
  error?: string;
  disabled?: boolean;
}

/** Standard text field: label, themed border (default/focus/error/disabled
 * states), and an error caption. */
export function AppInput({ label, error, disabled, style, onFocus, onBlur, ...rest }: AppInputProps) {
  const { theme } = useTheme();
  const [focused, setFocused] = useState(false);

  const borderColor = error
    ? theme.colors.statusDanger
    : focused
    ? theme.colors.borderFocus
    : theme.colors.borderDefault;

  return (
    <View>
      {label ? (
        <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>
          {label}
        </AppText>
      ) : null}
      <TextInput
        editable={!disabled}
        placeholderTextColor={theme.colors.textTertiary}
        onFocus={e => { setFocused(true); onFocus?.(e); }}
        onBlur={e => { setFocused(false); onBlur?.(e); }}
        accessibilityState={{ disabled: !!disabled }}
        style={[
          {
            minHeight: theme.touchTargets.minimum,
            borderWidth: 1,
            borderColor,
            borderRadius: theme.radiusUsage.input,
            paddingHorizontal: theme.spacing.base,
            color: disabled ? theme.colors.textDisabled : theme.colors.textPrimary,
            backgroundColor: disabled ? theme.colors.surfaceDisabled : theme.colors.surfaceDefault,
            ...theme.typography.body,
          },
          style,
        ]}
        {...rest}
      />
      {error ? (
        <AppText variant="caption" color="danger" style={{ marginTop: theme.spacing.xxs }}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
}
