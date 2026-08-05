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
import { loginWithPassword } from "../../api/session/sessionManager";
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
  const [screenError, setScreenError] = useState<string | undefined>();

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
    <AppScreen scroll style={{ backgroundColor: theme.colors.backgroundSunken }}>
      <View style={{ alignItems: "center", marginTop: theme.spacing.xxxl, marginBottom: theme.spacing.xxl }}>
        <FuvayMark />
      </View>
      <AppText variant="headingLarge" accessibilityRole="header" color="inverse" align="center">Sign in with password</AppText>
      <AppText variant="body" color="secondary" align="center" style={{ marginBottom: theme.spacing.xl }}>
        Use your email or mobile number.
      </AppText>

      {screenError ? <AuthErrorBanner message={screenError} /> : null}

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
        style={{ marginBottom: theme.spacing.base }}
      />
      <PasswordField
        value={password}
        onChangeText={value => { setPassword(value); setScreenError(undefined); }}
        disabled={submitting}
        autoComplete="current-password"
      />

      <View style={{ alignItems: "flex-end", marginTop: theme.spacing.xs, marginBottom: theme.spacing.xl }}>
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
      <View style={{ marginTop: theme.spacing.sm }}>
        <AppButton label="Use phone OTP instead" tone="secondary" onPress={() => navigation.navigate("LoginMethod")} fullWidth />
      </View>
    </AppScreen>
  );
}
