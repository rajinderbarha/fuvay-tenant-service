import React, { useId, useState } from "react";
import { View, TextInput, type TextInputProps, type KeyboardTypeOptions } from "react-native";
import { AppText } from "../primitives/AppText";
import { FieldMessage } from "./FieldMessage";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface AppTextFieldProps {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  helperText?: string;
  errorText?: string;
  required?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
  secureTextEntry?: boolean;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: TextInputProps["autoCapitalize"];
  textContentType?: TextInputProps["textContentType"];
  returnKeyType?: TextInputProps["returnKeyType"];
  leftIcon?: React.ReactNode;
  rightAction?: React.ReactNode;
  multiline?: boolean;
  maxLength?: number;
  showCharacterCount?: boolean;
  testID?: string;
  inputStyle?: TextInputProps["style"];
}

export function AppTextField({
  label,
  value,
  onChangeText,
  placeholder,
  helperText,
  errorText,
  required,
  disabled,
  readOnly,
  secureTextEntry,
  keyboardType,
  autoCapitalize,
  textContentType,
  returnKeyType,
  leftIcon,
  rightAction,
  multiline,
  maxLength,
  showCharacterCount,
  testID,
  inputStyle,
}: AppTextFieldProps) {
  const { theme } = useAppTheme();
  const fieldId = useId();
  const [focused, setFocused] = useState(false);
  const hasError = Boolean(errorText);

  const borderColor = hasError ? theme.colors.borderDanger : focused ? theme.colors.borderFocus : theme.colors.borderDefault;

  return (
    <View>
      {/* Label is always a real text node — never rely on placeholder alone. */}
      <AppText variant="labelMedium" color="textSecondary" nativeID={`${fieldId}-label`} style={{ marginBottom: theme.spacing[2] }}>
        {label}
        {required ? " *" : required === false ? " (optional)" : ""}
      </AppText>
      <View
        style={{
          flexDirection: "row",
          alignItems: multiline ? "flex-start" : "center",
          borderWidth: 1,
          borderColor,
          borderRadius: theme.radii.md,
          backgroundColor: disabled ? theme.colors.backgroundDisabled : theme.colors.surfacePrimary,
          paddingHorizontal: theme.spacing[5],
          minHeight: theme.sizes.inputHeight.md as number,
          gap: theme.spacing[3],
        }}
      >
        {leftIcon}
        <TextInput
          testID={testID}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={theme.colors.textTertiary}
          editable={!disabled && !readOnly}
          secureTextEntry={secureTextEntry}
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          textContentType={textContentType}
          returnKeyType={returnKeyType}
          multiline={multiline}
          maxLength={maxLength}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          accessibilityLabelledBy={`${fieldId}-label`}
          accessibilityState={{ disabled: Boolean(disabled) }}
          // Screen readers announce the invalid state via accessibilityInvalid + the FieldMessage below.
          aria-invalid={hasError}
          aria-required={required}
          style={[
            {
              flex: 1,
              paddingVertical: theme.spacing[3],
              color: disabled ? theme.colors.textDisabled : theme.colors.textPrimary,
              ...theme.typography.bodyMedium,
            },
            inputStyle,
          ]}
        />
        {rightAction}
      </View>
      {showCharacterCount && maxLength ? (
        <AppText variant="caption" color="textTertiary" align="right">
          {value.length}/{maxLength}
        </AppText>
      ) : null}
      {hasError ? <FieldMessage tone="error">{errorText}</FieldMessage> : helperText ? <FieldMessage tone="helper">{helperText}</FieldMessage> : null}
    </View>
  );
}
