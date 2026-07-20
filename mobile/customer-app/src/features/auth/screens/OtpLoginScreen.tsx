import React from "react";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppTextField } from "../../../components/forms/AppTextField";
import { useOtpFlow } from "../hooks/use-otp-flow";

/**
 * Single screen covering both OTP steps (phone entry, code verification) —
 * avoids passing hook state through navigation params, which would either
 * be non-serializable (functions) or lose state on unmount. Real
 * navigation away from this screen only happens once login succeeds (the
 * caller, e.g. RootNavigator, reacts to the resulting session change).
 */
export function OtpLoginScreen() {
  const flow = useOtpFlow();
  const isPhoneStep = flow.step === "enter-phone" || flow.step === "sending";

  return (
    <ScreenContainer>
      <Stack gap={7}>
        <AppText variant="headingLarge">Sign in</AppText>

        {isPhoneStep ? (
          <>
            <AppText variant="bodyMedium" color="textSecondary">
              Enter your phone number and we'll send you a one-time code.
            </AppText>
            <AppTextField
              label="Phone number"
              value={flow.phone}
              onChangeText={flow.setPhone}
              placeholder="+91XXXXXXXXXX"
              keyboardType="phone-pad"
              autoCapitalize="none"
              textContentType="telephoneNumber"
              errorText={flow.error ?? undefined}
              required
            />
            <AppButton label="Send code" onPress={flow.sendOtp} variant="primary" size="large" loading={flow.step === "sending"} />
          </>
        ) : (
          <>
            <AppText variant="bodyMedium" color="textSecondary">
              Enter the 6-digit code sent to {flow.phone}.
            </AppText>
            {flow.devOtpHint ? (
              <AppText variant="caption" color="textWarning">
                Dev only — code: {flow.devOtpHint}
              </AppText>
            ) : null}
            <AppTextField
              label="Verification code"
              value={flow.otp}
              onChangeText={flow.setOtp}
              placeholder="123456"
              keyboardType="number-pad"
              maxLength={6}
              errorText={flow.error ?? undefined}
              required
            />
            <AppButton label="Verify" onPress={() => void flow.verifyOtp()} variant="primary" size="large" loading={flow.step === "verifying"} />
            <AppButton label="Use a different number" onPress={flow.reset} variant="text" size="medium" />
          </>
        )}
      </Stack>
    </ScreenContainer>
  );
}
