import React, { useState, useCallback, useEffect, useRef } from "react";
import { View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { KeyboardAwareScreen } from "../../design-system/components/foundation/KeyboardAwareScreen";
import { Card, Section, Stack } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { LinkText } from "../../design-system/components/typography/LinkText";
import { OTPInput } from "../../design-system/components/forms/OTPInput";
import { PrimaryButton, TertiaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AuthHeader } from "./components/AuthHeader";
import * as authApi from "../../services/auth/authApi";
import { getOrCreateDeviceId } from "../../services/auth/deviceId";
import { useSession } from "../../navigation/session/SessionProvider";
import { AuthStackParamList } from "../../navigation/routeTypes";
import { AppError } from "../../services/api/types";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

type Props = NativeStackScreenProps<AuthStackParamList, "OtpVerify">;

const RESEND_COOLDOWN_SECONDS = 30;

/**
 * OTP code entry (Phase G spec section 4). Verification still passes
 * through MFA when the backend requires it (`verify_phone_otp_login`
 * returns the same mfa_required shape as password login).
 */
export function OtpVerifyScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { phone } = route.params;
  const { establishSession } = useSession();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";

  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);
  const cooldownTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    cooldownTimer.current = setInterval(() => setCooldown(c => (c > 0 ? c - 1 : 0)), 1000);
    return () => { if (cooldownTimer.current) clearInterval(cooldownTimer.current); };
  }, []);

  const submitCode = useCallback(async (submittedCode: string) => {
    if (submittedCode.length !== 6 || submitting || offline) return;
    setSubmitting(true);
    setError(null);
    try {
      const deviceId = await getOrCreateDeviceId();
      const result = await authApi.verifyOtp({ phone, otp: submittedCode, deviceId });
      if (!result.ok) {
        setError(result.error);
        setCode("");
        return;
      }
      const data = result.data;
      if (data.mfa_required) {
        navigation.navigate("Mfa", { mfaChallengeToken: data.mfa_challenge_token, rememberDevice: false });
        return;
      }
      if (!data.refresh_token) {
        setError({ code: "UNKNOWN_API_ERROR", category: "unknown", retryable: false, safeMessage: "Please contact your business administrator to finish setting up your account." });
        return;
      }
      await establishSession({ access_token: data.access_token, refresh_token: data.refresh_token });
    } finally {
      setSubmitting(false);
    }
  }, [phone, submitting, offline, establishSession, navigation]);

  const handleResend = useCallback(async () => {
    if (cooldown > 0 || resending || offline) return;
    setResending(true);
    setError(null);
    try {
      await authApi.sendOtp({ phone, purpose: "phone_login" });
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } finally {
      setResending(false);
    }
  }, [cooldown, resending, offline, phone]);

  return (
    <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
      <AuthHeader />
      <Section spacing="lg">
        <Heading level="large">Enter verification code</Heading>
        <AppText color="secondary" style={{ marginTop: 4 }}>
          We sent a 6-digit code to {phone}. It expires in a few minutes.
        </AppText>
      </Section>

      <Card>
        <Stack gap="base">
          {offline ? <InlineAlert tone="warning" title="You're offline" message="Connect to the internet to verify your code." /> : null}
          {error ? <InlineAlert tone="danger" title="Couldn't verify code" message={error.safeMessage} /> : null}

          <OTPInput
            length={6}
            value={code}
            onChange={value => { setCode(value); if (value.length === 6) submitCode(value); }}
            onSubmitEditing={() => submitCode(code)}
            label="Verification code"
            autoFocus
            disabled={submitting}
          />

          <PrimaryButton label="Verify" onPress={() => submitCode(code)} loading={submitting} disabled={code.length !== 6 || offline} fullWidth />

          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <TertiaryButton
              label={cooldown > 0 ? `Resend code (${cooldown}s)` : "Resend code"}
              onPress={handleResend}
              disabled={cooldown > 0 || resending || offline}
              loading={resending}
            />
            <LinkText onPress={() => navigation.goBack()} disabled={submitting}>Change number</LinkText>
          </View>
        </Stack>
      </Card>
    </KeyboardAwareScreen>
  );
}
