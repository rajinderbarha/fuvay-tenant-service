import React, { useState, useEffect, useRef } from "react";
import { View } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppIconButton } from "../../components";
import { Icon } from "../../components/Icon";
import { OtpCellInput } from "../../components/auth/OtpCellInput";
import { ResendCountdown } from "../../components/auth/ResendCountdown";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError, isRateLimited, retryAfterSecondsOf } from "../../components/auth/authErrorCopy";
import { maskPhoneForDisplay } from "../../domain/phone";
import {
  verifyLoginOtp, requestLoginOtp, verifyEmailLoginOtp, requestEmailLoginOtp,
} from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "VerifyLoginOtp">;
type Route = RouteProp<PublicStackParamList, "VerifyLoginOtp">;

/**
 * OTP outcomes this screen must branch on locally (mfa_required); every
 * other outcome (authenticated, session_expired, invalid_audience,
 * account_suspended) is handled globally by RootNavigator reacting to the
 * real session-state subscription (spec section 18: "Do not hardcode
 * navigation.navigate('Home')...") -- this screen only ever navigates to
 * MfaChallenge or back.
 */
export function VerifyLoginOtpScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  /**
   * One screen for both channels.
   *
   * `email` is set when the code was emailed instead of texted. Everything about
   * redeeming a 6-digit code is identical, so duplicating this screen would only
   * create two places for the attempt-limit and MFA branches to drift apart.
   */
  const { phone, email, devOtpHint } = route.params;
  const sentToEmail = !!email && !phone;
  const destinationLabel = sentToEmail ? (email as string) : maskPhoneForDisplay(phone as string);

  // Dev-only convenience: `devOtpHint` only ever exists outside production
  // (see LoginMethodScreen) -- pre-fills the code and auto-submits once, so
  // local testing never requires manually retyping the OTP.
  const [code, setCode] = useState(devOtpHint ?? "");
  const autoSubmittedRef = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [codeError, setCodeError] = useState<string | undefined>();
  const [screenError, setScreenError] = useState<string | undefined>();
  // No real cooldown/expiry metadata is returned by POST /v1/auth/otp/send
  // (verified this phase: OtpSendResponseDto has only message/use_verify/
  // otp_hint) -- resend starts available; a real countdown only appears
  // once the backend actually rate-limits and returns retry_after_seconds
  // (spec section 10: never hardcode a duration).
  const [resendCooldownUntil, setResendCooldownUntil] = useState<Date | null>(null);

  useEffect(() => {
    if (devOtpHint && devOtpHint.length === 6 && !autoSubmittedRef.current) {
      autoSubmittedRef.current = true;
      submitCode(devOtpHint);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitCode(value: string) {
    if (submitting || value.length !== 6) return;
    setSubmitting(true);
    setCodeError(undefined);
    setScreenError(undefined);
    try {
      const result = sentToEmail
        ? await verifyEmailLoginOtp(email as string, value)
        : await verifyLoginOtp(phone as string, value);
      if ("status" in result && result.status === "challenge_required") {
        navigation.navigate("MfaChallenge");
      }
      // Any other outcome (authenticated / suspended / invalid_audience)
      // is picked up globally -- nothing to do here.
    } catch (err) {
      if (isRateLimited(err)) {
        setScreenError(copyForAuthError(err));
      } else {
        setCodeError(copyForAuthError(err));
        setCode("");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    if (resending || resendCooldownUntil) return;
    setResending(true);
    setScreenError(undefined);
    try {
      if (sentToEmail) {
        await requestEmailLoginOtp(email as string);
      } else {
        await requestLoginOtp(phone as string);
      }
    } catch (err) {
      const retryAfter = retryAfterSecondsOf(err);
      if (isRateLimited(err) && retryAfter) {
        setResendCooldownUntil(new Date(Date.now() + retryAfter * 1000));
      } else {
        setScreenError(copyForAuthError(err));
      }
    } finally {
      setResending(false);
    }
  }

  return (
    <AppScreen scroll>
      <AppIconButton name="chevron-back" accessibilityLabel="Go back" onPress={() => navigation.goBack()} />
      <View style={{ marginTop: theme.spacing.xl }}>
        <AppText variant="headingLarge" accessibilityRole="header" align="center">
          {sentToEmail ? "Check your email" : "Verify your number"}
        </AppText>
        <AppText variant="body" color="secondary" align="center" style={{ marginTop: theme.spacing.xs, marginBottom: theme.spacing.xl }}>
          {`Enter the 6-digit code sent to ${destinationLabel}`}
        </AppText>

        {screenError ? <AuthErrorBanner message={screenError} /> : null}

        <OtpCellInput
          value={code}
          onChange={value => { setCode(value); setCodeError(undefined); }}
          onSubmitComplete={submitCode}
          errorText={codeError}
          disabled={submitting}
          autoFocus
        />

        <View style={{ marginTop: theme.spacing.xl }}>
          <AppButton
            label="Verify and continue"
            onPress={() => submitCode(code)}
            disabled={code.length !== 6}
            loading={submitting}
            fullWidth
          />
        </View>

        <View style={{ marginTop: theme.spacing.lg, alignItems: "center", gap: theme.spacing.sm }}>
          {resendCooldownUntil ? (
            <ResendCountdown cooldownUntil={resendCooldownUntil} onCooldownElapsed={() => setResendCooldownUntil(null)} />
          ) : (
            <AppText
              variant="bodySmall"
              color="link"
              accessibilityRole="button"
              onPress={handleResend}
            >
              {resending ? "Resending…" : "Resend code"}
            </AppText>
          )}
          <AppText variant="bodySmall" color="link" accessibilityRole="button" onPress={() => navigation.goBack()}>
            {/* "Change number" is wrong when the code went to an inbox. */}
            {sentToEmail ? "Change email" : "Change number"}
          </AppText>
        </View>

        <View style={{ flexDirection: "row", justifyContent: "center", alignItems: "center", gap: theme.spacing.xs, marginTop: theme.spacing.xxl }}>
          <Icon name="shield-checkmark-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary">Your sign-in is protected</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
