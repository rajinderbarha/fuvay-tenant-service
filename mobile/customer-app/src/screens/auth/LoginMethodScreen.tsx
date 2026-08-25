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
    /**
     * Composed as one centred column with the legal note pinned below it, rather than
     * a stack starting at the top: at this length the old layout left the whole lower
     * half of the screen empty, so the form read as the top fragment of a page that
     * had failed to finish loading.
     *
     * `scroll` stays for small devices and for when the keyboard is up; AppScreen
     * already grows its scroll content to fill the viewport, which is what lets the
     * column below centre when there is room to spare and scroll when there is not.
     */
    <AppScreen scroll>
      <View style={{ flex: 1, justifyContent: "center", paddingVertical: theme.spacing.xl }}>
        <View style={{ alignItems: "center", marginBottom: theme.spacing.xl }}>
          <FuvayMark />
        </View>

        <AppText variant="headingLarge" accessibilityRole="header" align="center">
          Welcome to Fuvay
        </AppText>
        <AppText
          variant="body"
          color="secondary"
          align="center"
          style={{ marginTop: theme.spacing.xxs, marginBottom: theme.spacing.xl }}
        >
          Book trusted services near you.
        </AppText>

        <LoginMethodSegmentedControl value={method} onChange={handleMethodChange} />

        {/* The banner sits between the control and the field, where it explains the
            thing directly under it, and takes no space when there is no error. */}
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
          />
        </View>

        <View style={{ marginTop: theme.spacing.lg }}>
          <AppButton label="Continue" onPress={handleContinue} loading={submitting} fullWidth />
        </View>

        {/* A new number cannot sign itself in here, so the way in has to be visible. */}
        <View style={{ marginTop: theme.spacing.base, alignItems: "center" }}>
          <AppText
            variant="bodySmall"
            color="link"
            accessibilityRole="link"
            accessibilityLabel="New to Fuvay? Create an account"
            onPress={() => navigation.navigate("Signup")}
          >
            New to Fuvay? Create an account
          </AppText>
        </View>
      </View>

      <View style={{ alignItems: "center", paddingBottom: theme.spacing.base }}>
        <LegalLinksFooter />
      </View>
    </AppScreen>
  );
}
