import React, { useState } from "react";
import { TextInput, TextInputProps, View } from "react-native";
import { useTheme } from "../../themes";
import { FieldLabel, FieldHelper, FormError, useFieldChrome } from "./FieldParts";

export interface TextFieldProps extends Omit<TextInputProps, "style"> {
  label?: string;
  helperText?: string;
  errorText?: string;
  required?: boolean;
  disabledReason?: string;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

/**
 * The base single-line input every text-entry field (Currency/Quantity/
 * Search/Password) composes. Business validation (e.g. "must be a valid
 * GSTIN") does not live here -- only generic label/value/helper/error
 * plumbing and the visual field chrome.
 */
export function TextField({
  label, helperText, errorText, required, disabledReason, leadingIcon, trailingIcon,
  editable = true, onFocus, onBlur, ...inputProps
}: TextFieldProps) {
  const { theme } = useTheme();
  const [focused, setFocused] = useState(false);
  const chrome = useFieldChrome({ error: !!errorText, disabled: !editable, focused });

  return (
    <View>
      {label ? <FieldLabel label={label} required={required} /> : null}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          paddingHorizontal: theme.spacing.md,
          minHeight: 48,
          gap: theme.spacing.xs,
          ...chrome,
        }}
      >
        {leadingIcon}
        <TextInput
          style={{ flex: 1, color: theme.colors.textPrimary, fontSize: theme.typography.body.fontSize, paddingVertical: theme.spacing.sm }}
          placeholderTextColor={theme.colors.textTertiary}
          editable={editable}
          onFocus={e => { setFocused(true); onFocus?.(e); }}
          onBlur={e => { setFocused(false); onBlur?.(e); }}
          accessibilityLabel={label}
          {...inputProps}
        />
        {trailingIcon}
      </View>
      {!editable && disabledReason ? <FieldHelper text={disabledReason} /> : <FieldHelper text={helperText} />}
      <FormError message={errorText} />
    </View>
  );
}
