import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppInput, AppIconButton } from "../../components";
import { PasswordField } from "../../components/auth/PasswordField";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { confirmPasswordReset } from "../../api/auth/authApi";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "ResetPasswordConfirm">;
type Route = RouteProp<PublicStackParamList, "ResetPasswordConfirm">;

/**
 * Step 2 of password recovery -- ONE combined screen for code + new
 * password (spec section 16), matching the Staff App's own established
 * pattern (mobile/staff-app routeTypes.ts `ResetPassword` comment) because
 * the backend itself is single-call: `POST /v1/auth/password/reset/confirm`
 * (AuthService.confirm_password_reset) verifies `reset_token` (the OTP)
 * and sets the new password atomically -- there is no separate "verify
 * code" endpoint to build a distinct step around.
 *
 * Confirmed in source: a successful reset revokes EVERY existing session
 * and returns only a message, never a new access/refresh token pair --
 * this screen must not auto-login; it always routes back to a fresh
 * sign-in on success.
 */
export function ResetPasswordConfirmScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { email, phone } = route.params;

  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [screenError, setScreenError] = useState<string | undefined>();
  const [fieldError, setFieldError] = useState<string | undefined>();

  async function handleSubmit() {
    if (submitting || !resetToken.trim() || !newPassword || !confirmPassword) return;
    if (newPassword !== confirmPassword) {
      setFieldError("Passwords don't match");
      return;
    }
    setFieldError(undefined);
    setScreenError(undefined);
    setSubmitting(true);
    try {
      await confirmPasswordReset({ email, phone, resetToken: resetToken.trim(), newPassword, confirmPassword });
      // Never auto-logs in (confirmed in source) -- return to sign-in.
      navigation.reset({ index: 0, routes: [{ name: "PasswordLogin" }] });
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
        <AppText variant="headingLarge" accessibilityRole="header" align="center">Enter your reset code</AppText>
        <AppText variant="body" color="secondary" align="center" style={{ marginTop: theme.spacing.xs, marginBottom: theme.spacing.xl }}>
          {`Enter the code sent to ${email ?? phone} and choose a new password.`}
        </AppText>

        {screenError ? <AuthErrorBanner message={screenError} /> : null}

        <AppInput
          label="Reset code"
          accessibilityLabel="Reset code"
          value={resetToken}
          onChangeText={value => { setResetToken(value); setScreenError(undefined); }}
          keyboardType="number-pad"
          editable={!submitting}
          style={{ marginBottom: theme.spacing.base }}
        />
        <PasswordField
          label="New password"
          value={newPassword}
          onChangeText={value => { setNewPassword(value); setFieldError(undefined); }}
          disabled={submitting}
          autoComplete="new-password"
        />
        <View style={{ marginTop: theme.spacing.base }}>
          <PasswordField
            label="Confirm new password"
            value={confirmPassword}
            onChangeText={value => { setConfirmPassword(value); setFieldError(undefined); }}
            disabled={submitting}
            autoComplete="new-password"
            error={fieldError}
          />
        </View>

        <View style={{ marginTop: theme.spacing.xl }}>
          <AppButton
            label="Reset password"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!resetToken.trim() || !newPassword || !confirmPassword}
            fullWidth
          />
        </View>
      </View>
    </AppScreen>
  );
}
