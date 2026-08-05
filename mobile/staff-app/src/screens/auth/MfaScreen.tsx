import React, { useState, useCallback } from "react";
import { View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { KeyboardAwareScreen } from "../../design-system/components/foundation/KeyboardAwareScreen";
import { Card, Section, Stack } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { LinkText } from "../../design-system/components/typography/LinkText";
import { OTPInput } from "../../design-system/components/forms/OTPInput";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AuthHeader } from "./components/AuthHeader";
import * as authApi from "../../services/auth/authApi";
import { getOrCreateDeviceId } from "../../services/auth/deviceId";
import { useSession } from "../../navigation/session/SessionProvider";
import { AuthStackParamList } from "../../navigation/routeTypes";
import { AppError } from "../../services/api/types";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

type Props = NativeStackScreenProps<AuthStackParamList, "Mfa">;

/**
 * MFA challenge (Phase G spec section 5). The challenge token is passed
 * through React Navigation's in-memory route params only -- never a
 * deep-link/URL parameter, never persisted to storage, and it goes out of
 * scope the moment this screen is left (back to Login or session
 * established). `rememberDevice` was captured on the Login/Otp screen and
 * is only actually applied here, after MFA succeeds (spec section 6:
 * "Device trust is earned only after successful MFA").
 */
export function MfaScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { mfaChallengeToken, rememberDevice } = route.params;
  const { establishSession } = useSession();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);

  const submit = useCallback(async (submittedCode: string) => {
    if (submittedCode.length < 6 || submitting || offline) return;
    setSubmitting(true);
    setError(null);
    try {
      const deviceId = await getOrCreateDeviceId();
      const result = await authApi.verifyMfa({ mfaChallengeToken, code: submittedCode, deviceId, rememberDevice });
      if (!result.ok) {
        setError(result.error);
        setCode("");
        return;
      }
      const data = result.data;
      if (data.mfa_required || !data.refresh_token) {
        // Defensive -- verify_mfa's real success shape never sets
        // mfa_required, but a challenge that's expired/invalid must never
        // be treated as a session establishment.
        setError({ code: "UNKNOWN_API_ERROR", category: "unknown", retryable: false, safeMessage: "Verification failed. Please try again." });
        return;
      }
      await establishSession({ access_token: data.access_token, refresh_token: data.refresh_token });
    } finally {
      setSubmitting(false);
    }
  }, [mfaChallengeToken, rememberDevice, submitting, offline, establishSession]);

  return (
    <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
      <AuthHeader />
      <Section spacing="lg">
        <Heading level="large">Verify it's you</Heading>
        <AppText color="secondary" style={{ marginTop: 4 }}>
          Enter the 6-digit code from your authenticator app, or a backup code.
        </AppText>
      </Section>

      <Card>
        <Stack gap="base">
          {offline ? <InlineAlert tone="warning" title="You're offline" message="Connect to the internet to verify." /> : null}
          {error ? <InlineAlert tone="danger" title="Verification failed" message={error.safeMessage} /> : null}

          <OTPInput
            length={6}
            value={code}
            onChange={value => { setCode(value); if (value.length === 6) submit(value); }}
            onSubmitEditing={() => submit(code)}
            label="Authenticator code"
            autoFocus
            disabled={submitting}
          />

          {rememberDevice ? (
            <AppText variant="caption" color="tertiary">
              This device will be remembered once verification succeeds, reducing how often you're asked for a code here.
            </AppText>
          ) : null}

          <PrimaryButton label="Verify" onPress={() => submit(code)} loading={submitting} disabled={code.length < 6 || offline} fullWidth />

          <View style={{ alignItems: "center" }}>
            <LinkText onPress={() => navigation.navigate("Login")} disabled={submitting}>Back to Login</LinkText>
          </View>
        </Stack>
      </Card>
    </KeyboardAwareScreen>
  );
}
