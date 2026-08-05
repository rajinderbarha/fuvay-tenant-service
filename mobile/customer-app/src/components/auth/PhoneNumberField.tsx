import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppInput } from "../AppInput";
import { CountryCode, DEFAULT_COUNTRY_CODE, SUPPORTED_COUNTRY_CODES, sanitizeNationalNumber } from "../../domain/phone";

export interface PhoneNumberFieldProps {
  countryCode: CountryCode;
  onCountryCodeChange: (country: CountryCode) => void;
  nationalNumber: string;
  onNationalNumberChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

/**
 * Country selector is limited to `SUPPORTED_COUNTRY_CODES` (spec section
 * 7: "Show only countries supported by current backend/product policy")
 * -- currently just India, cycling through the list on tap rather than a
 * full picker since there is only one option today; a real picker is a
 * one-line change to this component once a second country is approved,
 * not a rewrite.
 */
export function PhoneNumberField({
  countryCode, onCountryCodeChange, nationalNumber, onNationalNumberChange, error, disabled,
}: PhoneNumberFieldProps) {
  const { theme } = useTheme();

  function cycleCountry() {
    if (SUPPORTED_COUNTRY_CODES.length < 2) return;
    const currentIndex = SUPPORTED_COUNTRY_CODES.findIndex(c => c.code === countryCode.code);
    const next = SUPPORTED_COUNTRY_CODES[(currentIndex + 1) % SUPPORTED_COUNTRY_CODES.length];
    onCountryCodeChange(next);
  }

  return (
    <View>
      <AppText variant="label" color="secondary" style={{ marginBottom: theme.spacing.xxs }}>
        Mobile number
      </AppText>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View
          accessible
          accessibilityRole={SUPPORTED_COUNTRY_CODES.length > 1 ? "button" : undefined}
          accessibilityLabel={`Country code ${countryCode.code}`}
          onTouchEnd={cycleCountry}
          style={{
            minHeight: theme.touchTargets.minimum,
            paddingHorizontal: theme.spacing.base,
            borderWidth: 1,
            borderColor: theme.colors.borderDefault,
            borderRadius: theme.radiusUsage.input,
            backgroundColor: theme.colors.surfaceDefault,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <AppText variant="body">{countryCode.code}</AppText>
        </View>
        <AppInput
          style={{ flex: 1 }}
          value={nationalNumber}
          onChangeText={raw => onNationalNumberChange(sanitizeNationalNumber(raw))}
          keyboardType="phone-pad"
          textContentType="telephoneNumber"
          autoComplete="tel-national"
          maxLength={countryCode.nationalDigits}
          placeholder="98765 43210"
          editable={!disabled}
          error={error}
          accessibilityLabel="Mobile number"
        />
      </View>
    </View>
  );
}

export { DEFAULT_COUNTRY_CODE };
