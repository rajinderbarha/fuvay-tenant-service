import React, { useState } from "react";
import { TextInput, TextInputProps, View } from "react-native";
import { useTheme } from "../../themes";
import { FieldLabel, FieldHelper, FormError, useFieldChrome } from "./FieldParts";

export interface TextAreaProps extends Omit<TextInputProps, "style" | "multiline"> {
  label?: string;
  helperText?: string;
  errorText?: string;
  required?: boolean;
  minLines?: number;
}

export function TextArea({ label, helperText, errorText, required, minLines = 4, editable = true, onFocus, onBlur, ...inputProps }: TextAreaProps) {
  const { theme } = useTheme();
  const [focused, setFocused] = useState(false);
  const chrome = useFieldChrome({ error: !!errorText, disabled: !editable, focused });

  return (
    <View>
      {label ? <FieldLabel label={label} required={required} /> : null}
      <TextInput
        multiline
        textAlignVertical="top"
        style={{
          minHeight: minLines * 22,
          color: theme.colors.textPrimary,
          fontSize: theme.typography.body.fontSize,
          padding: theme.spacing.md,
          ...chrome,
        }}
        placeholderTextColor={theme.colors.textTertiary}
        editable={editable}
        onFocus={e => { setFocused(true); onFocus?.(e); }}
        onBlur={e => { setFocused(false); onBlur?.(e); }}
        accessibilityLabel={label}
        {...inputProps}
      />
      <FieldHelper text={helperText} />
      <FormError message={errorText} />
    </View>
  );
}
