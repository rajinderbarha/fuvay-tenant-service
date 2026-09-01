import React, { useState } from "react";
import { StyleProp, TextInput, TextInputProps, View, ViewStyle } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";
import { AppSurface } from "./AppSurface";

export interface AppInputProps extends TextInputProps {
  label?: string;
  error?: string;
  disabled?: boolean;
  /**
   * Style for the WRAPPER, not the field.
   *
   * `style` reaches the TextInput itself, which is why `style={{ flex: 1 }}` on a
   * field inside a row did nothing: the wrapper stayed content-width and the field
   * could not grow past it. That is what left the login screen's mobile number box
   * occupying half the row with dead space beside it.
   */
  containerStyle?: StyleProp<ViewStyle>;
}

/** Standard text field: label, themed border (default/focus/error/disabled
 * states), and an error caption.
 *
 * Forwards its ref to the underlying TextInput, so a caller can `blur()` the field
 * itself. That is not a convenience: a focused input inside a Modal keeps the
 * keyboard up when the Modal unmounts, and only blurring the real input releases it
 * (see LocationPickerModal). */
export const AppInput = React.forwardRef<TextInput, AppInputProps>(function AppInput(
  { label, error, disabled, style, containerStyle, onFocus, onBlur, ...rest }: AppInputProps,
  ref,
) {
  const { theme } = useTheme();
  const [focused, setFocused] = useState(false);

  const borderColor = error
    ? theme.colors.statusDanger
    : focused
    ? theme.colors.borderFocus
    : theme.colors.borderDefault;

  return (
    <View style={containerStyle}>
      {label ? (
        <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>
          {label}
        </AppText>
      ) : null}
      <AppSurface
        variant="inset"
        elevated={false}
        colors={disabled ? [theme.colors.surfaceDisabled, theme.colors.surfaceDisabled] : undefined}
        style={{ borderColor, borderRadius: theme.radiusUsage.input, overflow: "hidden" }}
      >
        <TextInput
          ref={ref}
          editable={!disabled}
          placeholderTextColor={theme.colors.textTertiary}
          onFocus={e => { setFocused(true); onFocus?.(e); }}
          onBlur={e => { setFocused(false); onBlur?.(e); }}
          accessibilityState={{ disabled: !!disabled }}
          style={[
            {
              minHeight: theme.touchTargets.minimum,
              borderWidth: 0,
              paddingHorizontal: theme.spacing.base,
              color: disabled ? theme.colors.textDisabled : theme.colors.textPrimary,
              backgroundColor: "transparent",
              ...theme.typography.body,
            },
            style,
          ]}
          {...rest}
        />
      </AppSurface>
      {error ? (
        <AppText variant="caption" color="danger" style={{ marginTop: theme.spacing.xxs }}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
});
