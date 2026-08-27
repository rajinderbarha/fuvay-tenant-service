import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppButton } from "../../components";
import { Icon } from "../../components/Icon";
import { PhoneNumberField } from "../../components/auth/PhoneNumberField";
import { LoginMethod } from "../../components/auth/LoginMethodSegmentedControl";
import { LoginExperienceShell } from "../../components/auth/LoginExperienceShell";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { DEFAULT_COUNTRY_CODE, isValidNationalNumber, toE164, CountryCode } from "../../domain/phone";
import { requestLoginOtp } from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";
import { ENV } from "../../config/environment";

type Nav = NativeStackNavigationProp<PublicStackParamList, "LoginMethod">;

/**
 * Primary customer authentication entry (spec section 7).
 *
 * OTP login does NOT create a user: `verify_phone_otp_login` raises the same
 * enumeration-safe error for an unknown number as for a wrong code. So this screen
 * must never imply that a new number can just "continue with OTP" -- it links to real
 * registration (`POST /v1/auth/register/customer`) instead, which is now wired.
 */
export function LoginMethodScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [method, setMethod] = useState<LoginMethod>("otp");
  const [countryCode, setCountryCode] = useState<CountryCode>(DEFAULT_COUNTRY_CODE);
  // Local-development convenience: EXPO_PUBLIC_DEV_PHONE prefills the field so
  // a test number does not have to be retyped on every reload. Unset outside
  // dev (and ignored in production builds), so the field starts empty for real
  // users -- same posture as the otp_hint guard below.
  const [nationalNumber, setNationalNumber] = useState(
    ENV.appEnv !== "production" ? (process.env.EXPO_PUBLIC_DEV_PHONE ?? "") : "",
  );
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [screenError, setScreenError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);

  function handleMethodChange(next: LoginMethod) {
    setMethod(next);
    setFieldError(undefined);
    setScreenError(undefined);
    if (next === "password") {
      navigation.navigate("PasswordLogin");
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
    <LoginExperienceShell
      method={method}
      onMethodChange={handleMethodChange}
      securityMessage="We'll send a secure verification code to your mobile number."
      onSignup={() => navigation.navigate("Signup")}
    >
        {screenError ? (
          <View style={{ marginTop: theme.spacing.base }}>
            <AuthErrorBanner message={screenError} />
          </View>
        ) : null}

        <View style={{ marginTop: theme.spacing.lg }}>
          <PhoneNumberField
            countryCode={countryCode}
            onCountryCodeChange={setCountryCode}
            nationalNumber={nationalNumber}
            onNationalNumberChange={value => { setNationalNumber(value); setFieldError(undefined); }}
            error={fieldError}
            disabled={submitting}
            showLabel={false}
            placeholder="Enter mobile number"
          />
        </View>

        <View style={{ marginTop: theme.spacing.lg }}>
          <AppButton
            label="Continue"
            onPress={handleContinue}
            loading={submitting}
            trailingIcon={<Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />}
            style={{ minHeight: 54 }}
            fullWidth
          />
        </View>
    </LoginExperienceShell>
  );
}
