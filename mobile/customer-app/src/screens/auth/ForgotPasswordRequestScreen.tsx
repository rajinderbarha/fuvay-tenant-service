import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppInput, AppIconButton } from "../../components";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { requestPasswordReset } from "../../api/auth/authApi";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "ForgotPasswordRequest">;

/**
 * Step 1 of password recovery (spec section 16). `AuthService.
 * request_password_reset` is enumeration-safe by construction (identical
 * response whether or not the account exists) -- this screen always
 * proceeds to ResetPasswordConfirm on a successful call, never branches
 * on account existence.
 */
export function ForgotPasswordRequestScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [identifier, setIdentifier] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [screenError, setScreenError] = useState<string | undefined>();

  const isEmail = identifier.includes("@");

  async function handleSubmit() {
    if (submitting || !identifier.trim()) return;
    setSubmitting(true);
    setScreenError(undefined);
    try {
      await requestPasswordReset(isEmail ? { email: identifier.trim() } : { phone: identifier.trim() });
      navigation.navigate("ResetPasswordConfirm", isEmail ? { email: identifier.trim() } : { phone: identifier.trim() });
    } catch (err) {
      setScreenError(copyForAuthError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppScreen scroll>
      <AppIconButton name="chevron-back" accessibilityLabel="Go back" onPress={() => navigation.goBack()} />
      <View style={{ marginTop: theme.spacing.xl }}>
        <AppText variant="headingLarge" accessibilityRole="header" align="center">Reset your password</AppText>
        <AppText variant="body" color="secondary" align="center" style={{ marginTop: theme.spacing.xs, marginBottom: theme.spacing.xl }}>
          Enter your email or mobile number and we'll send you a code if an account exists.
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
          editable={!submitting}
        />

        <View style={{ marginTop: theme.spacing.xl }}>
          <AppButton label="Send reset code" onPress={handleSubmit} loading={submitting} disabled={!identifier.trim()} fullWidth />
        </View>
      </View>
    </AppScreen>
  );
}
