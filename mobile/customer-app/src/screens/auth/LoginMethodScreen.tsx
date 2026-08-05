import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton } from "../../components";
import { FuvayMark } from "../../components/FuvayMark";
import { PhoneNumberField } from "../../components/auth/PhoneNumberField";
import { LoginMethodSegmentedControl, LoginMethod } from "../../components/auth/LoginMethodSegmentedControl";
import { LegalLinksFooter } from "../../components/auth/LegalLinksFooter";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { DEFAULT_COUNTRY_CODE, isValidNationalNumber, toE164, CountryCode } from "../../domain/phone";
import { requestLoginOtp } from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";
import { ENV } from "../../config/environment";

type Nav = NativeStackNavigationProp<PublicStackParamList, "LoginMethod">;

/**
 * Primary customer authentication entry (spec section 7). Matches the
 * attached design frame 1. `New customers can continue with OTP` from the
 * design is INTENTIONALLY OMITTED here -- verified this phase that
 * `verify_phone_otp_login` (app/engines/auth/service.py) does NOT create
 * a user; it raises the same enumeration-safe error for an unknown number
 * as for a wrong code. There is no just-in-time customer creation on the
 * OTP-login path; `/v1/auth/register/customer` is a separate, explicit
 * registration call this phase does not wire in (see Phase G report
 * "backend gaps"). Showing that helper text would misrepresent what
 * actually happens for a genuinely new phone number.
 */
export function LoginMethodScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [method, setMethod] = useState<LoginMethod>("otp");
  const [countryCode, setCountryCode] = useState<CountryCode>(DEFAULT_COUNTRY_CODE);
  const [nationalNumber, setNationalNumber] = useState("");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [screenError, setScreenError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);

  function handleMethodChange(next: LoginMethod) {
    setMethod(next);
    setFieldError(undefined);
    setScreenError(undefined);
    if (next === "password") {
      navigation.navigate("PasswordLogin");
      // Reset back to 'otp' for when the customer returns via back
      // navigation -- the segmented control on THIS screen must not carry
      // over a stale 'password' selection once PasswordLogin is its own
      // route (spec section 12: preserve only safe input, no sensitive
      // carry-over between methods).
      setMethod("otp");
    }
  }

  async function handleContinue() {
    if (submitting) return; // prevents duplicate submissions from a double-tap
    if (!isValidNationalNumber(nationalNumber, countryCode)) {
      setFieldError(`Enter a valid ${countryCode.nationalDigits}-digit mobile number`);
      return;
    }
    setFieldError(undefined);
    setScreenError(undefined);
    setSubmitting(true);
    try {
      const phone = toE164(nationalNumber, countryCode);
      const result = await requestLoginOtp(phone);
      // `otp_hint` only ever exists on the DTO outside production (backend's
      // own rule) -- the `appEnv !== "production"` check here is a second,
      // redundant guard so a local build can never carry it forward even if
      // pointed at a misconfigured non-prod-labeled backend.
      const devOtpHint = ENV.appEnv !== "production" ? result.otp_hint : undefined;
      navigation.navigate("VerifyLoginOtp", { phone, devOtpHint });
    } catch (err) {
      setScreenError(copyForAuthError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppScreen scroll>
      <View style={{ alignItems: "center", marginTop: theme.spacing.xxxl, marginBottom: theme.spacing.xxl }}>
        <FuvayMark />
      </View>
      <AppText variant="headingLarge" accessibilityRole="header" align="center">Welcome to Fuvay</AppText>
      <AppText variant="body" color="secondary" align="center" style={{ marginBottom: theme.spacing.xl }}>
        Book trusted services near you.
      </AppText>

      <LoginMethodSegmentedControl value={method} onChange={handleMethodChange} />

      <View style={{ marginTop: theme.spacing.xl }}>
        {screenError ? <AuthErrorBanner message={screenError} /> : null}
        <PhoneNumberField
          countryCode={countryCode}
          onCountryCodeChange={setCountryCode}
          nationalNumber={nationalNumber}
          onNationalNumberChange={value => { setNationalNumber(value); setFieldError(undefined); }}
          error={fieldError}
          disabled={submitting}
        />
      </View>

      <View style={{ marginTop: theme.spacing.xl }}>
        <AppButton label="Continue" onPress={handleContinue} loading={submitting} fullWidth />
      </View>

      <View style={{ marginTop: theme.spacing.xxl, alignItems: "center", gap: theme.spacing.lg }}>
        <LegalLinksFooter />
      </View>
    </AppScreen>
  );
}
