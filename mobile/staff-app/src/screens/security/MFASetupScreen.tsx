import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PasswordField } from "../../design-system/components/forms/PasswordField";
import { Checkbox } from "../../design-system/components/forms/Checkbox";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import * as mfaApi from "../../services/auth/mfaApi";
import { useSecurity } from "./useSecurity";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "MFASetup">;

/**
 * MFA Enrollment (Phase V spec section 6). The TOTP secret is shown ONLY
 * during this in-memory setup step -- never written to AsyncStorage or
 * SecureStore, never logged. Backup codes (if the server returns any) are
 * shown once and require explicit confirmation they were saved.
 */
export function MFASetupScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { invalidate } = useSecurity();
  const [step, setStep] = useState<"start" | "confirm" | "codes">("start");
  const [otpauthUrl, setOtpauthUrl] = useState<string | null>(null);
  const [manualKey, setManualKey] = useState<string | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState("");
  const [codesSavedConfirmed, setCodesSavedConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleStart = async () => {
    setError(null);
    setBusy(true);
    const result = await mfaApi.setupMfa();
    setBusy(false);
    if (result.ok) {
      setOtpauthUrl(result.data.otpauth_url ?? null);
      setManualKey(result.data.secret ?? null);
      setStep("confirm");
    } else {
      setError(result.error.safeMessage);
    }
  };

  const handleConfirm = async () => {
    setError(null);
    setBusy(true);
    const result = await mfaApi.confirmMfa(code);
    setBusy(false);
    if (result.ok) {
      invalidate();
      if (result.data.backup_codes && result.data.backup_codes.length > 0) {
        setBackupCodes(result.data.backup_codes);
        setStep("codes");
      } else {
        navigation.goBack();
      }
    } else {
      setError(result.error.safeMessage);
    }
  };

  if (step === "codes" && backupCodes) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Save recovery codes" onBack={() => navigation.goBack()} />
        <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="warning" title="Save these codes now" message="Each code can be used once to sign in if you lose access to your authenticator app. They won't be shown again." />
          <View style={{ height: theme.spacing.base }} />
          <Card>
            {backupCodes.map(c => <AppText key={c} variant="bodyStrong" style={{ fontFamily: "monospace", marginBottom: 4 }}>{c}</AppText>)}
          </Card>
          <View style={{ height: theme.spacing.base }} />
          <Checkbox label="I've saved these recovery codes somewhere safe" checked={codesSavedConfirmed} onChange={setCodesSavedConfirmed} />
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="Done" onPress={() => navigation.goBack()} disabled={!codesSavedConfirmed} fullWidth />
        </ScrollView>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Set up two-step verification" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {step === "start" ? (
          <>
            <Section>
              <AppText variant="bodySmall" color="tertiary">
                You'll need an authenticator app (like Google Authenticator or Authy). We'll show a setup key to scan or enter manually.
              </AppText>
            </Section>
            {error ? <InlineAlert tone="danger" title="Couldn't start setup" message={error} /> : null}
            <PrimaryButton label="Start setup" onPress={handleStart} loading={busy} fullWidth />
          </>
        ) : (
          <>
            <Section>
              <Card>
                <AppText variant="bodyStrong">Manual setup key</AppText>
                <AppText variant="bodySmall" color="tertiary" selectable style={{ fontFamily: "monospace", marginTop: theme.spacing.xs }}>
                  {manualKey ?? otpauthUrl ?? "Unavailable"}
                </AppText>
                <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
                  Enter this key in your authenticator app, then type the 6-digit code it shows.
                </AppText>
              </Card>
            </Section>
            <Section>
              <PasswordField label="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />
            </Section>
            {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Invalid code" message={error} /></View> : null}
            <PrimaryButton label="Confirm" onPress={handleConfirm} loading={busy} disabled={code.length < 6} fullWidth />
          </>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
