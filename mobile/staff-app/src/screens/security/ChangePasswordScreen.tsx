import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PasswordField } from "../../design-system/components/forms/PasswordField";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import * as authApi from "../../services/auth/authApi";
import { useSecurity } from "./useSecurity";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "ChangePassword">;

const REQUIREMENTS: { test: (v: string) => boolean; label: string }[] = [
  { test: v => v.length >= 8, label: "At least 8 characters" },
  { test: v => /[A-Z]/.test(v), label: "One uppercase letter" },
  { test: v => /[0-9]/.test(v), label: "One number" },
];

/** Change Password (Phase V spec section 5). Server remains authoritative
 * for password policy -- the checklist below is real-time usability
 * feedback only, never a client-side maximum or the actual gate. */
export function ChangePasswordScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { invalidate } = useSecurity();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ sessionsRevoked: number } | null>(null);

  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
  const canSubmit = currentPassword.length > 0 && passwordsMatch && REQUIREMENTS.every(r => r.test(newPassword));

  const handleSubmit = async () => {
    setError(null);
    setBusy(true);
    try {
      const response = await authApi.changePassword({ currentPassword, newPassword, confirmPassword });
      if (response.ok) {
        setResult({ sessionsRevoked: response.data.other_sessions_revoked });
        invalidate();
      } else {
        // Generic message regardless of whether it was the current-password
        // check or a policy failure -- never leaks which one (spec section 5, 14).
        setError(response.error.safeMessage);
      }
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Change password" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Password changed" message="Your password was updated successfully." />
          <View style={{ height: theme.spacing.base }} />
          <InlineAlert
            tone="neutral"
            message={result.sessionsRevoked > 0
              ? `${result.sessionsRevoked} other signed-in device${result.sessionsRevoked === 1 ? "" : "s"} ${result.sessionsRevoked === 1 ? "was" : "were"} signed out for your security. This device stays signed in.`
              : "No other devices were signed in, so nothing else was affected."}
          />
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="Done" onPress={() => navigation.goBack()} fullWidth />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Change password" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card style={{ gap: theme.spacing.sm }}>
            <PasswordField label="Current password" value={currentPassword} onChangeText={setCurrentPassword} textContentType="password" autoComplete="current-password" />
            <PasswordField label="New password" value={newPassword} onChangeText={setNewPassword} textContentType="newPassword" autoComplete="new-password" />
            <PasswordField label="Confirm new password" value={confirmPassword} onChangeText={setConfirmPassword} textContentType="newPassword" autoComplete="new-password" />
          </Card>
        </Section>

        <Section>
          <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>Password requirements</AppText>
          {REQUIREMENTS.map(req => (
            <AppText key={req.label} variant="bodySmall" color={req.test(newPassword) ? "success" : "tertiary"}>
              {req.test(newPassword) ? "✓" : "•"} {req.label}
            </AppText>
          ))}
          {newPassword.length > 0 && confirmPassword.length > 0 && !passwordsMatch ? (
            <AppText variant="bodySmall" color="danger">Passwords don't match</AppText>
          ) : null}
        </Section>

        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't change password" message={error} /></View> : null}

        <PrimaryButton label="Change password" onPress={handleSubmit} loading={busy} disabled={!canSubmit} fullWidth />
      </ScrollView>
    </SafeAreaScreen>
  );
}
