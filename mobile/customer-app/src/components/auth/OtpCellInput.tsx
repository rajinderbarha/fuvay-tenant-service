import React, { useRef } from "react";
import { View, TextInput, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";

export interface OtpCellInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  onSubmitComplete?: (value: string) => void;
  disabled?: boolean;
  errorText?: string;
  autoFocus?: boolean;
}

/**
 * Renders as N visual cells but is ONE logical accessible input (spec
 * section 9 "OTP input requirements" / section 22 accessibility) --
 * accomplished with a single TextInput stretched over the whole cell row
 * (opacity 0, but full-size so tapping anywhere in the row focuses it and
 * the OS keyboard/autofill/paste all attach to a single real field), with
 * the cells below purely decorative (`accessibilityElementsHidden`). The
 * same component is reused for MFA authenticator/recovery codes.
 */
export function OtpCellInput({
  length = 6, value, onChange, onSubmitComplete, disabled, errorText, autoFocus,
}: OtpCellInputProps) {
  const { theme } = useTheme();
  const inputRef = useRef<TextInput>(null);

  function handleChangeText(raw: string) {
    // Numeric only, capped at `length` -- a paste of a longer/garbled
    // string (e.g. "Your code is: 284176") is sanitized, not rejected.
    const digitsOnly = raw.replace(/\D/g, "").slice(0, length);
    onChange(digitsOnly);
    if (digitsOnly.length === length) {
      onSubmitComplete?.(digitsOnly);
    }
  }

  return (
    <View>
      <Pressable onPress={() => inputRef.current?.focus()} style={{ position: "relative" }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", gap: theme.spacing.sm }}>
          {Array.from({ length }).map((_, i) => {
            const filled = i < value.length;
            const isActive = i === value.length;
            return (
              <View
                key={i}
                accessibilityElementsHidden
                importantForAccessibility="no-hide-descendants"
                style={{
                  flex: 1,
                  aspectRatio: 1,
                  borderRadius: theme.radiusUsage.input,
                  borderWidth: isActive ? 2 : 1,
                  borderColor: errorText ? theme.colors.statusDanger : isActive ? theme.colors.borderFocus : theme.colors.borderDefault,
                  backgroundColor: theme.colors.surfaceDefault,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <AppText variant="headingSmall">{filled ? value[i] : ""}</AppText>
              </View>
            );
          })}
        </View>
        <TextInput
          ref={inputRef}
          value={value}
          onChangeText={handleChangeText}
          keyboardType="number-pad"
          textContentType="oneTimeCode"
          autoComplete="sms-otp"
          maxLength={length}
          editable={!disabled}
          autoFocus={autoFocus}
          accessibilityLabel="Verification code"
          accessibilityHint={`Enter the ${length}-digit code`}
          style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, opacity: 0 }}
        />
      </Pressable>
      {errorText ? (
        <AppText variant="caption" color="danger" style={{ marginTop: theme.spacing.xs }} accessibilityLiveRegion="polite">
          {errorText}
        </AppText>
      ) : null}
    </View>
  );
}
