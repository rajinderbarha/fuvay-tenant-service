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
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AuthHeader } from "./components/AuthHeader";
import * as authApi from "../../services/auth/authApi";
import { AuthStackParamList } from "../../navigation/routeTypes";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

type Props = NativeStackScreenProps<AuthStackParamList, "ForgotPassword">;

const ENUMERATION_SAFE_MESSAGE = "If this account exists, a reset code has been sent.";

/** Password-reset request (Phase G spec section 7). Always shows the same
 * enumeration-safe confirmation, matching the backend's own
 * `request_password_reset` behavior verbatim. */
export function ForgotPasswordScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";

  const [identifier, setIdentifier] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const isEmail = identifier.includes("@");
  const canSubmit = identifier.trim().length > 0 && !submitting && !offline;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setNetworkError(null);
    try {
      const trimmed = identifier.trim();
      const result = await authApi.requestPasswordReset(isEmail ? { email: trimmed } : { phone: trimmed });
      if (!result.ok && result.error.category === "network") {
        setNetworkError(result.error.safeMessage);
        return;
      }
      // Enumeration-safe: shown identically whether or not the account exists.
      setSent(true);
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, identifier, isEmail]);

  if (sent) {
    return (
      <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
        <AuthHeader />
        <Card>
          <Stack gap="base">
            <Heading level="medium">Check your messages</Heading>
            <AppText color="secondary">{ENUMERATION_SAFE_MESSAGE}</AppText>
            <PrimaryButton
              label="I have a code"
              onPress={() => navigation.navigate("ResetPassword", { identifier: isEmail ? { email: identifier.trim() } : { phone: identifier.trim() } })}
              fullWidth
            />
            <View style={{ alignItems: "center" }}>
              <LinkText onPress={() => navigation.navigate("Login")}>Back to Login</LinkText>
            </View>
          </Stack>
        </Card>
      </KeyboardAwareScreen>
    );
  }

  return (
    <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
      <AuthHeader />
      <Section spacing="lg">
        <Heading level="large">Forgot password</Heading>
        <AppText color="secondary" style={{ marginTop: 4 }}>
          Enter your email or mobile number and we'll send you a reset code.
        </AppText>
      </Section>

      <Card>
        <Stack gap="base">
          {offline ? <InlineAlert tone="warning" title="You're offline" message="Connect to the internet to request a reset code." /> : null}
          {networkError ? <InlineAlert tone="danger" title="Couldn't send reset code" message={networkError} /> : null}

          <TextField
            label="Email or mobile number"
            placeholder="Enter email or mobile"
            value={identifier}
            onChangeText={setIdentifier}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!submitting}
            returnKeyType="go"
            onSubmitEditing={handleSubmit}
          />
          <PrimaryButton label="Send reset code" onPress={handleSubmit} loading={submitting} disabled={!canSubmit} fullWidth />
          <View style={{ alignItems: "center" }}>
            <LinkText onPress={() => navigation.navigate("Login")} disabled={submitting}>Back to Login</LinkText>
          </View>
        </Stack>
      </Card>
    </KeyboardAwareScreen>
  );
}
