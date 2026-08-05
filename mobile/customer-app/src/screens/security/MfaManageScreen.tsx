import React, { useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppButton } from "../../components/AppButton";
import { AppCard } from "../../components/AppCard";
import { AppInput } from "../../components/AppInput";
import { LoadingState } from "../../components/LoadingState";
import { PasswordField } from "../../components/auth/PasswordField";
import { SecurityHeader } from "../../components/security/SecurityHeader";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useSetupMfaMutation, useConfirmMfaMutation, useDisableMfaMutation } from "../../api/customerSecurity/useMfaMutations";
import { DomainError } from "../../domain/errors";

/**
 * Covers both enrollment (spec section 8) and disable (fresh
 * verification, canonical policy = current password + TOTP code) --
 * driven by the real `is_mfa_enabled` flag rather than a route param, so
 * it can never show a stale mode. Backup codes are shown exactly once,
 * held only in local component state (never cached/persisted -- cleared
 * the moment the customer leaves this screen), with an explicit
 * acknowledgement gate before `Done` is enabled.
 */
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "MfaManage">;

export function MfaManageScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const profileQuery = useCustomerProfileQuery();
  const setupMutation = useSetupMfaMutation();
  const confirmMutation = useConfirmMfaMutation();
  const disableMutation = useDisableMfaMutation();

  const [enrollment, setEnrollment] = useState<{ secret: string; backupCodes: string[] } | null>(null);
  const [code, setCode] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");

  if (profileQuery.isPending) {
    return <AppScreen><LoadingState label="Loading" /></AppScreen>;
  }

  const mfaEnabled = profileQuery.data?.mfaEnabled ?? false;

  async function handleBeginSetup() {
    setError(null);
    try {
      const res = await setupMutation.mutateAsync();
      setEnrollment({ secret: res.data.secret, backupCodes: res.data.backup_codes });
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't start setup. Please try again.");
    }
  }

  async function handleConfirm() {
    setError(null);
    if (code.length !== 6) return;
    try {
      await confirmMutation.mutateAsync(code);
      setConfirmed(true);
      setCode("");
    } catch (err) {
      setError(err instanceof DomainError ? err.diagnostic : "Invalid code. Please try again.");
    }
  }

  async function handleDisable() {
    setError(null);
    if (!disablePassword || !disableCode) return;
    try {
      await disableMutation.mutateAsync({ password: disablePassword, code: disableCode });
      setDisablePassword(""); setDisableCode("");
      navigation.goBack();
    } catch (err) {
      setDisablePassword(""); setDisableCode("");
      setError(err instanceof DomainError ? err.diagnostic : "Couldn't disable two-step verification.");
    }
  }

  function confirmDisable() {
    Alert.alert(
      "Turn off two-step verification?",
      "Your account will be less protected. This requires your password and current code.",
      [{ text: "Keep it on", style: "cancel" }, { text: "Continue", style: "destructive", onPress: handleDisable }],
    );
  }

  if (mfaEnabled) {
    return (
      <AppScreen scroll edges={["top", "bottom"]}>
        <View style={{ gap: theme.spacing.base }}>
          <SecurityHeader onBack={() => navigation.goBack()} />
          <AppCard style={{ gap: theme.spacing.sm }}>
            <AppText variant="bodyStrong">Turn off two-step verification</AppText>
            <AppText variant="bodySmall" color="secondary">Requires your password and a current code to confirm it's really you.</AppText>
            <PasswordField label="Password" value={disablePassword} onChangeText={t => { setDisablePassword(t); setError(null); }} autoComplete="current-password" disabled={disableMutation.isPending} />
            <AppInput label="6-digit code or backup code" value={disableCode} onChangeText={t => { setDisableCode(t); setError(null); }} keyboardType="number-pad" maxLength={8} accessibilityLabel="Verification code" editable={!disableMutation.isPending} />
            {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}
            <AppButton
              label="Turn off two-step verification" tone="destructive"
              onPress={confirmDisable}
              loading={disableMutation.isPending}
              disabled={!disablePassword || !disableCode}
              fullWidth
            />
            {disableMutation.isPending ? <AppText variant="caption" color="secondary" align="center">Securing your account…</AppText> : null}
          </AppCard>
        </View>
      </AppScreen>
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <SecurityHeader onBack={() => navigation.goBack()} />

        {!enrollment ? (
          <AppCard style={{ gap: theme.spacing.sm }}>
            <AppText variant="bodyStrong">Set up two-step verification</AppText>
            <AppText variant="bodySmall" color="secondary">
              You'll need an authenticator app (like Google Authenticator or Authy) to scan or enter a setup key.
            </AppText>
            {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}
            <AppButton label="Begin setup" onPress={handleBeginSetup} loading={setupMutation.isPending} fullWidth />
          </AppCard>
        ) : !confirmed ? (
          <>
            <AppCard style={{ gap: theme.spacing.sm }}>
              <AppText variant="bodyStrong">Enter this setup key in your authenticator app</AppText>
              <AppText variant="body" style={{ fontFamily: "monospace" }} selectable>{enrollment.secret}</AppText>
            </AppCard>
            <AppCard style={{ gap: theme.spacing.sm }}>
              <AppText variant="bodyStrong">Save your backup codes</AppText>
              <AppText variant="bodySmall" color="secondary">
                Use one of these to sign in if you lose access to your authenticator app. Each code works once. Save them somewhere safe -- they won't be shown again.
              </AppText>
              <View style={{ gap: theme.spacing.xxs }}>
                {enrollment.backupCodes.map(c => (
                  <AppText key={c} variant="body" style={{ fontFamily: "monospace" }} selectable>{c}</AppText>
                ))}
              </View>
              <AppText
                variant="labelStrong" color={acknowledged ? "secondary" : "link"}
                onPress={() => setAcknowledged(v => !v)}
                accessibilityRole="checkbox" accessibilityState={{ checked: acknowledged }}
                accessibilityLabel="I have saved my backup codes"
              >
                {acknowledged ? "✓ I've saved my backup codes" : "I've saved my backup codes"}
              </AppText>
            </AppCard>
            <AppCard style={{ gap: theme.spacing.sm }}>
              <AppText variant="bodyStrong">Enter the 6-digit code from your app</AppText>
              <AppInput
                value={code} onChangeText={t => { setCode(t.replace(/[^0-9]/g, "").slice(0, 6)); setError(null); }}
                keyboardType="number-pad" maxLength={6} accessibilityLabel="Verification code"
                editable={!confirmMutation.isPending}
              />
              {error ? <AppText variant="bodySmall" color="danger">{error}</AppText> : null}
              <AppButton
                label="Confirm and turn on" onPress={handleConfirm}
                loading={confirmMutation.isPending}
                disabled={!acknowledged || code.length !== 6}
                fullWidth
              />
              {confirmMutation.isPending ? <AppText variant="caption" color="secondary" align="center">Securing your account…</AppText> : null}
            </AppCard>
          </>
        ) : (
          <AppCard style={{ gap: theme.spacing.sm, alignItems: "center" }}>
            <AppText variant="bodyStrong">Two-step verification is on</AppText>
            <AppText variant="bodySmall" color="secondary" align="center">Your account now requires a code at sign-in.</AppText>
            <AppButton label="Done" onPress={() => navigation.goBack()} fullWidth />
          </AppCard>
        )}
      </View>
    </AppScreen>
  );
}
