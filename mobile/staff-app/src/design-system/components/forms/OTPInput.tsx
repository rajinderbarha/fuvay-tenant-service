import React, { useRef } from "react";
import { View, TextInput, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { FieldHelper, FormError } from "./FieldParts";

export interface OTPInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  onSubmitEditing?: () => void;
  label?: string;
  helperText?: string;
  errorText?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

/**
 * Verification-code entry (Phase G spec section 4). A single hidden
 * TextInput captures the digits (so iOS/Android SMS autofill and manual
 * paste both work correctly) while N visual boxes reflect its value --
 * this is the standard, most accessible pattern for OTP entry on mobile
 * (screen readers get one real text field, not N confusing single-char ones).
 */
export function OTPInput({ length = 6, value, onChange, onSubmitEditing, label, helperText, errorText, disabled, autoFocus }: OTPInputProps) {
  const { theme } = useTheme();
  const inputRef = useRef<TextInput>(null);
  const digits = value.padEnd(length, " ").split("").slice(0, length);

  return (
    <View>
      {label ? <AppText variant="label" style={{ marginBottom: theme.spacing.xs }}>{label}</AppText> : null}
      <Pressable onPress={() => inputRef.current?.focus()} accessibilityRole="none">
        <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
          {digits.map((digit, index) => {
            const isCursor = index === value.length;
            return (
              <View
                key={index}
                style={{
                  flex: 1, height: 52, borderRadius: theme.radiusUsage.input, borderWidth: isCursor ? 2 : 1,
                  borderColor: errorText ? theme.colors.statusDanger : isCursor ? theme.colors.brandPrimary : theme.colors.borderDefault,
                  backgroundColor: theme.colors.surfaceDefault, alignItems: "center", justifyContent: "center",
                  opacity: disabled ? theme.opacity.disabled : 1,
                }}
              >
                <AppText variant="bodyStrong">{digit.trim()}</AppText>
              </View>
            );
          })}
        </View>
      </Pressable>
      <TextInput
        ref={inputRef}
        value={value}
        onChangeText={text => onChange(text.replace(/[^0-9]/g, "").slice(0, length))}
        onSubmitEditing={onSubmitEditing}
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="sms-otp"
        autoFocus={autoFocus}
        editable={!disabled}
        maxLength={length}
        accessibilityLabel={label ?? "Verification code"}
        accessibilityHint={`Enter the ${length}-digit code`}
        // Visually hidden but still focusable/accessible -- the boxes above
        // are decorative reflections of this field's real value.
        style={{ position: "absolute", opacity: 0, height: 1, width: 1 }}
      />
      <FieldHelper text={helperText} />
      <FormError message={errorText} />
    </View>
  );
}
