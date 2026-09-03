import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppInput } from "../../components";
import { FuvayMark } from "../../components/FuvayMark";
import { PhoneNumberField } from "../../components/auth/PhoneNumberField";
import { LegalLinksFooter } from "../../components/auth/LegalLinksFooter";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForSignupError } from "../../components/auth/authErrorCopy";
import { DEFAULT_COUNTRY_CODE, isValidNationalNumber, toE164, CountryCode } from "../../domain/phone";
import { registerCustomer } from "../../api/auth/authApi";
import { PublicStackParamList } from "../../navigation/routeTypes";
import { ENV } from "../../config/environment";

type Nav = NativeStackNavigationProp<PublicStackParamList, "Signup">;

const NAME_MIN = 2;
const NAME_MAX = 255;

/**
 * Customer signup.
 *
 * Real gap this closes: there was none. OTP login does not create a user --
 * `verify_phone_otp_login` raises the same enumeration-safe error for an unknown
 * number as for a wrong code -- so someone installing the app had no way in at all,
 * and the only route to an account was for somebody else to create it.
 *
 * Verified live against `POST /v1/auth/register/customer`: 201, the account exists,
 * and a phone-OTP login on the new number returns a real session that can load the
 * customer's Home.
 *
 * Two deliberate choices:
 *
 *  - Only what the backend actually stores is asked for: full name, phone, and an
 *    optional email. No address, no password. The account is usable immediately and
 *    the first address is collected where it is actually needed, during a booking.
 *  - Verification reuses the SAME screen a returning customer uses. Registration
 *    sends one redeemable login OTP; the app never requests a duplicate code.
 */
export function SignupScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [fullName, setFullName] = useState("");
  const [countryCode, setCountryCode] = useState<CountryCode>(DEFAULT_COUNTRY_CODE);
  const [nationalNumber, setNationalNumber] = useState("");
  const [email, setEmail] = useState("");
  const [nameError, setNameError] = useState<string | undefined>();
  const [phoneError, setPhoneError] = useState<string | undefined>();
  const [screenError, setScreenError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);

  async function handleCreateAccount() {
    if (submitting) return;

    // Mirrors the backend's own constraints (RegisterCustomerRequest), never
    // stricter: full_name 2..255, phone E.164.
    const name = fullName.trim().replace(/\s+/g, " ");
    let invalid = false;
    if (name.length < NAME_MIN || name.length > NAME_MAX) {
      setNameError(`Enter your name (at least ${NAME_MIN} characters)`);
      invalid = true;
    }
    if (!isValidNationalNumber(nationalNumber, countryCode)) {
      setPhoneError(`Enter a valid ${countryCode.nationalDigits}-digit mobile number`);
      invalid = true;
    }
    if (invalid) return;

    setNameError(undefined);
    setPhoneError(undefined);
    setScreenError(undefined);
    setSubmitting(true);
    const phone = toE164(nationalNumber, countryCode);
    try {
      const registration = await registerCustomer({
        fullName: name,
        phone,
        email: email.trim() || undefined,
      });
      const devOtpHint = ENV.appEnv !== "production"
        ? registration.data.otp_hint
        : undefined;
      navigation.navigate("VerifyLoginOtp", { phone, devOtpHint });
    } catch (err) {
      // Signup copy, not login copy: "We couldn't sign you in with those details" is
      // nonsense here, and the one case worth naming -- this number already has an
      // account -- is about a number the customer just typed themselves.
      setScreenError(copyForSignupError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppScreen scroll>
      <View style={{ flex: 1, justifyContent: "center", paddingVertical: theme.spacing.xl }}>
        <View style={{ alignItems: "center", marginBottom: theme.spacing.xl }}>
          <FuvayMark />
        </View>

        <AppText variant="headingLarge" accessibilityRole="header" align="center">
          Create your account
        </AppText>
        <AppText
          variant="body"
          color="secondary"
          align="center"
          style={{ marginTop: theme.spacing.xxs, marginBottom: theme.spacing.xl }}
        >
          We&apos;ll text you a code to confirm your number.
        </AppText>

        {screenError ? (
          <View style={{ marginBottom: theme.spacing.base }}>
            <AuthErrorBanner message={screenError} />
          </View>
        ) : null}

        <AppInput
          label="Full name"
          accessibilityLabel="Full name"
          value={fullName}
          onChangeText={value => { setFullName(value); setNameError(undefined); }}
          autoCapitalize="words"
          textContentType="name"
          autoComplete="name"
          maxLength={NAME_MAX}
          editable={!submitting}
          error={nameError}
          containerStyle={{ marginBottom: theme.spacing.base }}
        />

        <PhoneNumberField
          countryCode={countryCode}
          onCountryCodeChange={setCountryCode}
          nationalNumber={nationalNumber}
          onNationalNumberChange={value => { setNationalNumber(value); setPhoneError(undefined); }}
          error={phoneError}
          disabled={submitting}
        />

        <View style={{ marginTop: theme.spacing.base }}>
          {/* Genuinely optional, and labelled as such rather than collected because a
              form looks more complete with it. The backend stores an internal
              placeholder when there is none. */}
          <AppInput
            label="Email (optional)"
            accessibilityLabel="Email, optional"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            autoComplete="email"
            editable={!submitting}
          />
        </View>

        <View style={{ marginTop: theme.spacing.lg }}>
          <AppButton
            label="Create account"
            onPress={handleCreateAccount}
            loading={submitting}
            fullWidth
          />
        </View>

        <View style={{ marginTop: theme.spacing.base, alignItems: "center" }}>
          <AppText
            variant="bodySmall"
            color="link"
            accessibilityRole="link"
            accessibilityLabel="I already have an account"
            onPress={() => navigation.navigate("LoginMethod")}
          >
            I already have an account
          </AppText>
        </View>
      </View>

      <View style={{ alignItems: "center", paddingBottom: theme.spacing.base }}>
        <LegalLinksFooter />
      </View>
    </AppScreen>
  );
}
