import React from "react";
import { Pressable, TextInput, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppLucideIcon } from "../AppLucideIcon";
import { CountryCode, DEFAULT_COUNTRY_CODE, SUPPORTED_COUNTRY_CODES, isValidNationalNumber, sanitizeNationalNumber } from "../../domain/phone";

export interface PhoneNumberFieldProps {
  countryCode: CountryCode;
  onCountryCodeChange: (country: CountryCode) => void;
  nationalNumber: string;
  onNationalNumberChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  showLabel?: boolean;
  placeholder?: string;
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
  showLabel = true, placeholder = "98765 43210",
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
      {showLabel ? <AppText variant="metaLabel" style={{ marginBottom: 9, color: theme.fuvay.surfaces.faint }}>MOBILE NUMBER</AppText> : null}
      <View style={{ minHeight: 58, flexDirection: "row", alignItems: "stretch", borderRadius: 18, overflow: "hidden", borderWidth: 1.5, borderColor: error ? theme.colors.statusDanger : theme.fuvay.accents.a2, backgroundColor: theme.fuvay.surfaces.card }}>
        <Pressable
          accessibilityRole={SUPPORTED_COUNTRY_CODES.length > 1 ? "button" : undefined}
          accessibilityLabel={`Country code ${countryCode.code}`}
          onPress={cycleCountry}
          disabled={SUPPORTED_COUNTRY_CODES.length < 2 || disabled}
          style={{ paddingHorizontal: 15, flexDirection: "row", alignItems: "center", gap: 6 }}
        >
          <AppText variant="bodyStrong" style={{ color: theme.fuvay.surfaces.text, fontSize: 14 }}>{countryCode.code}</AppText>
          <AppLucideIcon name="chevron-down" size={13} color={theme.fuvay.surfaces.faint} strokeWidth={2} />
        </Pressable>
        <View style={{ width: 1, backgroundColor: theme.fuvay.surfaces.rule, marginVertical: 12 }} />
        <View style={{ flex: 1, minWidth: 0, paddingHorizontal: 15, flexDirection: "row", alignItems: "center", gap: 10 }}>
          <TextInput
            value={nationalNumber}
            onChangeText={raw => onNationalNumberChange(sanitizeNationalNumber(raw))}
            keyboardType="phone-pad"
            textContentType="telephoneNumber"
            autoComplete="tel-national"
            maxLength={countryCode.nationalDigits}
            placeholder={placeholder}
            placeholderTextColor={theme.fuvay.surfaces.faint}
            editable={!disabled}
            accessibilityLabel="Mobile number"
            style={[theme.typography.body, { flex: 1, minWidth: 0, paddingVertical: 0, color: theme.fuvay.surfaces.text, fontSize: 16, letterSpacing: 0.96 }]}
          />
          {isValidNationalNumber(nationalNumber, countryCode) ? <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: theme.fuvay.accents.a3, alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="check" size={13} color={theme.fuvay.ink(theme.fuvay.accents.a3)} strokeWidth={3} /></View> : null}
        </View>
      </View>
      {error ? <AppText variant="caption" style={{ marginTop: 6, color: theme.colors.statusDanger }}>{error}</AppText> : null}
    </View>
  );
}

export { DEFAULT_COUNTRY_CODE };
