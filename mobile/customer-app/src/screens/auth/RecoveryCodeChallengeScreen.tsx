import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen, AppText, AppButton, AppInput } from "../../components";
import { Icon } from "../../components/Icon";
import { AuthErrorBanner } from "../../components/auth/AuthErrorBanner";
import { copyForAuthError } from "../../components/auth/authErrorCopy";
import { completeMfaChallenge } from "../../api/session/sessionManager";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "RecoveryCodeChallenge">;

/**
 * Recovery-code fallback for the SAME MFA challenge as MfaChallengeScreen
 * (spec section 14). Verified in source: `/v1/auth/mfa/verify` accepts
 * either a 6-digit TOTP code OR a backup code through the identical
 * `code` field (AuthService.verify_mfa tries TOTP first, then falls back
 * to backup-code verification) -- there is no separate recovery-code
 * endpoint, so this screen calls the exact same `completeMfaChallenge`.
 * Backup codes have no fixed digit-only format (`MFAVerifyRequest.code`
 * allows 6-8 characters), so this uses a plain text field, not the
 * 6-digit OtpCellInput.
 */
export function RecoveryCodeChallengeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [screenError, setScreenError] = useState<string | undefined>();

  async function handleVerify() {
    if (submitting || code.trim().length < 6) return;
    setSubmitting(true);
    setScreenError(undefined);
    try {
      await completeMfaChallenge(code.trim());
      // Authenticated outcome is handled globally by RootNavigator.
    } catch (err) {
      setScreenError(copyForAuthError(err));
      setCode("");
    } finally {
      setSubmitting(false);
    }
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
        <Icon name="key" size="feature" color={theme.colors.brandPrimaryStrong} decorative />
      </View>
      <AppText variant="headingLarge" accessibilityRole="header" color="inverse" align="center">Use a recovery code</AppText>
      <AppText variant="body" color="secondary" align="center" style={{ marginBottom: theme.spacing.xl }}>
        Enter one of the recovery codes you saved when you set up two-factor authentication.
      </AppText>

      {screenError ? <AuthErrorBanner message={screenError} /> : null}

      <AppInput
        value={code}
        onChangeText={value => { setCode(value); setScreenError(undefined); }}
        autoCapitalize="characters"
        autoCorrect={false}
        placeholder="XXXX-XXXX"
        editable={!submitting}
        accessibilityLabel="Recovery code"
        style={{ width: "100%" }}
      />

      <View style={{ width: "100%", marginTop: theme.spacing.xl, gap: theme.spacing.sm }}>
        <AppButton label="Verify" onPress={handleVerify} loading={submitting} disabled={code.trim().length < 6} fullWidth />
        <AppButton label="Use authenticator code instead" tone="secondary" onPress={() => navigation.goBack()} fullWidth />
      </View>
    </AppScreen>
  );
}
