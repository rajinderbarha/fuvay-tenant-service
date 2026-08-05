import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton } from "../../components";
import { Icon } from "../../components/Icon";
import { OtpCellInput } from "../../components/auth/OtpCellInput";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { completeMfaChallenge } from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "MfaChallenge">;

/**
 * MFA authenticator challenge (spec section 13). Reads no route params --
 * the challenge token lives only in sessionManager's module state
 * (never a route URL, per spec). Successful completion is picked up
 * globally by RootNavigator; this screen only handles the code-entry
 * failure states and the switch to recovery-code mode.
 */
export function MfaChallengeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [codeError, setCodeError] = useState<string | undefined>();
  const [screenError, setScreenError] = useState<string | undefined>();

  async function submit(value: string) {
    if (submitting || value.length < 6) return;
    setSubmitting(true);
    setCodeError(undefined);
    setScreenError(undefined);
    try {
      await completeMfaChallenge(value);
      // Authenticated outcome is handled globally by RootNavigator.
    } catch (err) {
      setCodeError(copyForAuthError(err));
      setCode("");
    } finally {
      setSubmitting(false);
    }
  }

  function handleUseRecoveryCode() {
    // Switching to recovery-code MODE for the SAME challenge -- this must
    // NOT clear the challenge token (see RecoveryCodeChallengeScreen,
    // which verifies against the identical pending token). `cancelMfaChallenge`
    // is reserved for a genuine abandonment path (e.g. a future explicit
    // "back to login" action), which this screen does not expose per the
    // approved design (no back arrow on this frame).
    navigation.navigate("RecoveryCodeChallenge");
  }

  return (
    <AppScreen scroll style={{ backgroundColor: theme.colors.backgroundSunken, alignItems: "center" }}>
      <View
        style={{
          width: 88, height: 88, borderRadius: theme.radius.radiusFull,
          backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center",
          marginTop: theme.spacing.xxxl, marginBottom: theme.spacing.xl,
        }}
      >
        <Icon name="shield-checkmark" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
      </View>
      <AppText variant="headingLarge" accessibilityRole="header" color="inverse" align="center">Security check</AppText>
      <AppText variant="body" color="secondary" align="center" style={{ marginBottom: theme.spacing.xl }}>
        Enter the code from your authenticator app.
      </AppText>

      {screenError ? <AuthErrorBanner message={screenError} /> : null}

      <View style={{ width: "100%" }}>
        <OtpCellInput value={code} onChange={value => { setCode(value); setCodeError(undefined); }} onSubmitComplete={submit} errorText={codeError} disabled={submitting} autoFocus />
      </View>

      <View style={{ width: "100%", marginTop: theme.spacing.xl, gap: theme.spacing.sm }}>
        <AppButton label="Verify" onPress={() => submit(code)} loading={submitting} disabled={code.length < 6} fullWidth />
        <AppButton label="Use a recovery code" tone="secondary" onPress={handleUseRecoveryCode} fullWidth />
      </View>

      <AppText variant="bodySmall" color="link" style={{ marginTop: theme.spacing.xl }} onPress={() => { /* Phase G: no support route wired yet -- see navigationActions.openHelpAndSupport */ }}>
        Need help?
      </AppText>
    </AppScreen>
  );
}
