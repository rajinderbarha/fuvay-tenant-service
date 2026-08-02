import React, { useState, useCallback, useEffect } from "react";
import { View } from "react-native";
import Constants from "expo-constants";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { KeyboardAwareScreen } from "../../design-system/components/foundation/KeyboardAwareScreen";
import { Card, Section, Stack } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { LinkText } from "../../design-system/components/typography/LinkText";
import { TextField } from "../../design-system/components/forms/TextField";
import { PasswordField } from "../../design-system/components/forms/PasswordField";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { SegmentedControl } from "../../design-system/components/forms/SegmentedControl";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { AuthHeader } from "./components/AuthHeader";
import { ServiceHealthBadge } from "./components/ServiceHealthBadge";
import * as authApi from "../../services/auth/authApi";
import { getOrCreateDeviceId } from "../../services/auth/deviceId";
import { useSession } from "../../navigation/session/SessionProvider";
import { AuthStackParamList } from "../../navigation/routeTypes";
import { AppError } from "../../services/api/types";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { loadQueue } from "../../services/sync/queueStorage";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

/**
 * Password + Mobile-OTP login (Phase G spec sections 1, 3). Never navigates
 * directly to Home on a token response -- it only calls
 * `establishSession()` (Phase F) and lets Phase E's RootNavigator react to
 * the resolved access context. A pending deep link, if any, is revalidated
 * by DeepLinkHandler once bootstrapState reaches authenticated_ready, not
 * consumed here.
 */
export function LoginScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { establishSession, lastKnownScope } = useSession();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const sessionExpired = route.params?.reasonCode === "SESSION_EXPIRED";

  const [method, setMethod] = useState<"password" | "otp">("password");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberDevice, setRememberDevice] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [phoneForOtp, setPhoneForOtp] = useState("");
  const [preservedDraftCount, setPreservedDraftCount] = useState<number | null>(null);

  // Real, not fabricated: counts whatever is actually still sitting in the
  // offline queue for the technician who was just signed out, scoped to
  // their own last-known user+tenant key -- never a made-up number.
  useEffect(() => {
    if (!sessionExpired || !lastKnownScope) return;
    loadQueue(lastKnownScope.userId, lastKnownScope.tenantId).then(items => {
      setPreservedDraftCount(items.filter(i => i.state !== "server_confirmed" && i.state !== "cancelled").length);
    });
  }, [sessionExpired, lastKnownScope?.userId, lastKnownScope?.tenantId]);

  const canSubmitPassword = identifier.trim().length > 0 && password.length > 0 && !submitting && !offline;
  const canSendOtp = phoneForOtp.trim().length > 0 && !submitting && !offline;

  const handlePasswordLogin = useCallback(async () => {
    if (!canSubmitPassword) return;
    setSubmitting(true);
    setError(null);
    try {
      const deviceId = await getOrCreateDeviceId();
      const result = await authApi.login({ email: identifier.trim(), password, deviceId, rememberDevice });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      const data = result.data;
      if (data.mfa_required) {
        navigation.navigate("Mfa", { mfaChallengeToken: data.mfa_challenge_token, rememberDevice });
        return;
      }
      if (!data.refresh_token) {
        // requires_password_change or similar -- Phase G doesn't implement
        // the change-password screen; fail safely rather than crash on the
        // missing refresh_token establishSession requires.
        setError({
          code: "UNKNOWN_API_ERROR", category: "unknown", retryable: false,
          safeMessage: "Your password must be changed before you can sign in. Contact your business administrator.",
        });
        return;
      }
      await establishSession({ access_token: data.access_token, refresh_token: data.refresh_token });
      // No navigation call here -- RootNavigator resets based on the
      // newly-resolved bootstrapState once establishSession updates context.
    } finally {
      setSubmitting(false);
    }
  }, [canSubmitPassword, identifier, password, rememberDevice, establishSession, navigation]);

  const handleSendOtp = useCallback(async () => {
    if (!canSendOtp) return;
    setSubmitting(true);
    setError(null);
    try {
      const phone = phoneForOtp.trim();
      const result = await authApi.sendOtp({ phone, purpose: "phone_login" });
      // Enumeration-safe regardless of ok/not-found -- only a hard
      // network/validation failure surfaces as an error.
      if (!result.ok && (result.error.category === "network" || result.error.category === "validation")) {
        setError(result.error);
        return;
      }
      navigation.navigate("OtpVerify", { phone });
    } finally {
      setSubmitting(false);
    }
  }, [canSendOtp, phoneForOtp, navigation]);

  return (
    <KeyboardAwareScreen contentContainerStyle={{ padding: theme.spacing.lg, flexGrow: 1, justifyContent: "center" }}>
      <AuthHeader />

      <Section spacing="lg">
        <Heading level="large">Welcome back</Heading>
        <AppText color="secondary" style={{ marginTop: 4, marginBottom: theme.spacing.sm }}>
          Sign in to view your assigned work and manage service jobs.
        </AppText>
        {sessionExpired ? (
          <InlineAlert
            tone="info"
            title="Please sign in again"
            message={
              preservedDraftCount === null
                ? "Your session expired to keep your account secure. Any pending uploads are paused, not lost."
                : `Your session expired to keep your account secure. ${preservedDraftCount} local draft${preservedDraftCount === 1 ? "" : "s"} preserved on this device -- pending uploads stay paused until you sign back in.`
            }
          />
        ) : null}
        <ServiceHealthBadge />
      </Section>

      <Card>
        <Stack gap="base">
          <SegmentedControl
            options={[{ value: "password", label: "Password" }, { value: "otp", label: "Mobile OTP" }]}
            value={method}
            onChange={setMethod}
            disabled={submitting}
          />

          {offline ? <InlineAlert tone="warning" title="You're offline" message="Connect to the internet to sign in." /> : null}
          {error ? <InlineAlert tone="danger" title="Couldn't sign in" message={error.safeMessage} /> : null}

          {method === "password" ? (
            <>
              <TextField
                label="Email or mobile number"
                placeholder="Enter email or mobile"
                value={identifier}
                onChangeText={setIdentifier}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                textContentType="username"
                autoComplete="username"
                editable={!submitting}
                returnKeyType="next"
              />
              <PasswordField
                label="Password"
                placeholder="Enter password"
                value={password}
                onChangeText={setPassword}
                editable={!submitting}
                returnKeyType="go"
                onSubmitEditing={handlePasswordLogin}
              />
              <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                <Checkbox label="Remember this device" checked={rememberDevice} onChange={setRememberDevice} disabled={submitting} />
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <LinkText onPress={() => navigation.navigate("ForgotPassword")} disabled={submitting}>Forgot password?</LinkText>
              </View>
              <PrimaryButton label="Sign in" onPress={handlePasswordLogin} loading={submitting} disabled={!canSubmitPassword} fullWidth />
            </>
          ) : (
            <>
              <TextField
                label="Mobile number"
                placeholder="Enter mobile number"
                value={phoneForOtp}
                onChangeText={setPhoneForOtp}
                keyboardType="phone-pad"
                textContentType="telephoneNumber"
                autoComplete="tel"
                editable={!submitting}
                returnKeyType="go"
                onSubmitEditing={handleSendOtp}
              />
              <PrimaryButton label="Send code" onPress={handleSendOtp} loading={submitting} disabled={!canSendOtp} fullWidth />
            </>
          )}

          <View style={{ alignItems: "center", marginTop: theme.spacing.xs }}>
            <AppText variant="caption" color="tertiary">Protected by ServiceOS secure authentication</AppText>
          </View>
        </Stack>
      </Card>

      <View style={{ marginTop: theme.spacing.lg, alignItems: "center" }}>
        <AppText variant="bodySmall" color="secondary" align="center">Your business manages technician access.</AppText>
        {/* No pre-authenticated support destination exists (Help & Support
         * lives inside the authenticated Profile stack) -- this is
         * deliberately plain, non-interactive text rather than a dead
         * onPress, per the release-certification pass's dead-button sweep. */}
        <AppText variant="bodySmall" color="tertiary">Contact your business admin if you need help signing in.</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.sm }}>
          App version {Constants.expoConfig?.version ?? "1.0.0"} ({Constants.expoConfig?.android?.versionCode ?? Constants.expoConfig?.ios?.buildNumber ?? "1"})
        </AppText>
      </View>
    </KeyboardAwareScreen>
  );
}
