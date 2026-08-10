import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppInput } from "../../components";
import { FuvayMark } from "../../components/FuvayMark";
import { PasswordField } from "../../components/auth/PasswordField";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { ENV } from "../../config/environment";
import { loginWithPassword, requestEmailLoginOtp } from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "PasswordLogin">;

/**
 * Password fallback (spec section 11). `LoginRequest.email` accepts EITHER
 * a normalized email OR an E.164 mobile in the same field (verified in
 * source: `_normalise_email` validator, and `AuthService.login`'s
 * `"@" not in email` branch) -- this screen therefore uses ONE combined
 * identifier field, never separate email/phone inputs, matching the
 * backend's real contract exactly.
 */
export function PasswordLoginScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [screenError, setScreenError] = useState<string | undefined>();

  // Offered only for something that looks like an email, because the code is emailed.
  // An "@" is the whole test on purpose: the backend validates the address, and being
  // stricter here would refuse valid addresses this app has no business judging.
  const identifierLooksLikeEmail = identifier.includes("@");

  /**
   * Emails a sign-in code instead of asking for the password.
   *
   * The endpoint's response is identical whether or not the address has an account, so
   * this screen cannot and does not tell the customer which -- it says a code is on the
   * way if an account exists, and moves to the code screen either way. Anything else
   * would turn this form into an account-existence oracle.
   */
  async function handleEmailCode() {
    if (sendingCode || !identifierLooksLikeEmail) return;
    const email = identifier.trim();
    setSendingCode(true);
    setScreenError(undefined);
    try {
      const res = await requestEmailLoginOtp(email);
      const devOtpHint = ENV.appEnv !== "production" ? res.otp_hint : undefined;
      navigation.navigate("VerifyLoginOtp", { email, devOtpHint });
    } catch (err) {
      setScreenError(copyForAuthError(err));
    } finally {
      setSendingCode(false);
    }
  }

  async function handleSignIn() {
    if (submitting || !identifier.trim() || !password) return;
    setSubmitting(true);
    setScreenError(undefined);
    try {
      const result = await loginWithPassword({ email: identifier.trim(), password });
      if ("status" in result && result.status === "challenge_required") {
        navigation.navigate("MfaChallenge");
      }
      // Authenticated / suspended / invalid_audience is handled globally.
      // Password is intentionally NOT cleared on success -- the screen
      // unmounts as RootNavigator resets to the customer/exceptional
      // stack. It IS cleared below on a terminal failure.
    } catch (err) {
      setScreenError(copyForAuthError(err));
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    /**
     * Laid out exactly like the OTP screen: one centred column, same spacing scale.
     * The two are the same decision seen twice, so they should not look like two
     * different products.
     *
     * The heading was `color="inverse"` on a `backgroundSunken` screen -- white text
     * on #EAEFF8 in light mode and near-black on #161618 in dark. The title was
     * invisible in BOTH themes. It uses the ordinary screen background and default
     * text colour now, which is legible by construction.
     */
    <AppScreen scroll>
      <View style={{ flex: 1, justifyContent: "center", paddingVertical: theme.spacing.xl }}>
        <View style={{ alignItems: "center", marginBottom: theme.spacing.xl }}>
          <FuvayMark />
        </View>

        <AppText variant="headingLarge" accessibilityRole="header" align="center">
          Sign in with password
        </AppText>
        <AppText
          variant="body"
          color="secondary"
          align="center"
          style={{ marginTop: theme.spacing.xxs, marginBottom: theme.spacing.xl }}
        >
          Use your email or mobile number.
        </AppText>

        {screenError ? (
          <View style={{ marginBottom: theme.spacing.base }}>
            <AuthErrorBanner message={screenError} />
          </View>
        ) : null}

        <AppInput
          label="Email or mobile"
          accessibilityLabel="Email or mobile"
          value={identifier}
          onChangeText={value => { setIdentifier(value); setScreenError(undefined); }}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          textContentType="username"
          autoComplete="username"
          editable={!submitting}
          // The WRAPPER, not the field: `style` reaches the TextInput, so this margin
          // used to sit inside the box and pushed the error caption around instead of
          // separating the two fields.
          containerStyle={{ marginBottom: theme.spacing.base }}
        />
        <PasswordField
          value={password}
          onChangeText={value => { setPassword(value); setScreenError(undefined); }}
          disabled={submitting}
          autoComplete="current-password"
        />

        <View style={{ alignItems: "flex-end", marginTop: theme.spacing.xs, marginBottom: theme.spacing.lg }}>
          <AppText variant="bodySmall" color="link" accessibilityRole="link" onPress={() => navigation.navigate("ForgotPasswordRequest")}>
            Forgot password?
          </AppText>
        </View>

        <AppButton
          label="Sign in"
          onPress={handleSignIn}
          loading={submitting}
          disabled={!identifier.trim() || !password}
          fullWidth
        />
        {/* Only for an email identifier -- the code goes to an inbox, so offering it
            beside a phone number would be a button that cannot work. */}
        {identifierLooksLikeEmail ? (
          <View style={{ marginTop: theme.spacing.sm }}>
            <AppButton
              label="Email me a code instead"
              tone="secondary"
              onPress={handleEmailCode}
              loading={sendingCode}
              fullWidth
            />
          </View>
        ) : null}

        <View style={{ marginTop: theme.spacing.sm }}>
          <AppButton label="Use phone OTP instead" tone="secondary" onPress={() => navigation.navigate("LoginMethod")} fullWidth />
        </View>

        {/* A password screen is where someone discovers they have no account. */}
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
    </AppScreen>
  );
}
