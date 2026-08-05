import React, { useState, useCallback } from "react";
import { View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { KeyboardAwareScreen } from "../../design-system/components/foundation/KeyboardAwareScreen";
import { Card, Section, Stack } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { LinkText } from "../../design-system/components/typography/LinkText";
import { TextField } from "../../design-system/components/forms/TextField";
import { PasswordField } from "../../design-system/components/forms/PasswordField";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AuthHeader } from "./components/AuthHeader";
import * as authApi from "../../services/auth/authApi";
import { AuthStackParamList } from "../../navigation/routeTypes";
import { AppError } from "../../services/api/types";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

type Props = NativeStackScreenProps<AuthStackParamList, "ResetPassword">;

/** Real backend password policy (app/engines/auth/utils.py
 * validate_password_strength) -- shown here verbatim, nothing invented. */
const PASSWORD_REQUIREMENTS = "At least 8 characters, with an uppercase letter, a lowercase letter, a number and a special character.";

export function ResetPasswordScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { identifier } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [mismatchError, setMismatchError] = useState<string | null>(null);

  const canSubmit = code.trim().length >= 6 && newPassword.length >= 8 && confirmPassword.length >= 8 && !submitting && !offline;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    if (newPassword !== confirmPassword) {
      setMismatchError("Passwords don't match.");
      return;
    }
    setMismatchError(null);
    setSubmitting(true);
    setError(null);
    try {
      const result = await authApi.confirmPasswordReset({
        email: identifier.email, phone: identifier.phone,
        resetToken: code.trim(), newPassword, confirmPassword,
      });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      // Backend revokes every existing session on a successful reset --
      // no local session/challenge state exists to clear here (Phase G
      // never establishes a session mid-reset), so this just navigates on.
      navigation.reset({ index: 0, routes: [{ name: "ResetSuccess" }] });
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, code, newPassword, confirmPassword, identifier, navigation]);

  return (
    <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
      <AuthHeader />
      <Section spacing="lg">
        <Heading level="large">Reset your password</Heading>
        <AppText color="secondary" style={{ marginTop: 4 }}>Enter the code we sent you and choose a new password.</AppText>
      </Section>

      <Card>
        <Stack gap="base">
          {offline ? <InlineAlert tone="warning" title="You're offline" message="Connect to the internet to reset your password." /> : null}
          {error ? <InlineAlert tone="danger" title="Couldn't reset password" message={error.safeMessage} /> : null}
          {mismatchError ? <InlineAlert tone="danger" title="Passwords don't match" message={mismatchError} /> : null}

          <TextField
            label="Reset code"
            placeholder="Enter the code you received"
            value={code}
            onChangeText={setCode}
            keyboardType="number-pad"
            editable={!submitting}
          />
          <PasswordField
            label="New password"
            placeholder="Enter new password"
            value={newPassword}
            onChangeText={setNewPassword}
            helperText={PASSWORD_REQUIREMENTS}
            editable={!submitting}
            textContentType="newPassword"
          />
          <PasswordField
            label="Confirm new password"
            placeholder="Re-enter new password"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            editable={!submitting}
            textContentType="newPassword"
            returnKeyType="go"
            onSubmitEditing={handleSubmit}
          />
          <PrimaryButton label="Reset password" onPress={handleSubmit} loading={submitting} disabled={!canSubmit} fullWidth />
          <View style={{ alignItems: "center" }}>
            <LinkText onPress={() => navigation.navigate("Login")} disabled={submitting}>Back to Login</LinkText>
          </View>
        </Stack>
      </Card>
    </KeyboardAwareScreen>
  );
}
