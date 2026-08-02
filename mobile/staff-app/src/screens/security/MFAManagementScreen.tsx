import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { KeyValueList, SectionHeader } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { PasswordField } from "../../design-system/components/forms/PasswordField";
import { PrimaryButton, SecondaryButton, DestructiveButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import * as mfaApi from "../../services/auth/mfaApi";
import { useSecurity } from "./useSecurity";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "MFAManagement">;

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";

/**
 * MFA Management (Phase V spec section 8, 9). Disabling requires password +
 * current code and is unconditionally rejected server-side if the
 * organization requires MFA (`required_by_policy`) -- shown here as a
 * locked state, not a client-side guess.
 */
export function MFAManagementScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { data, isLoading, invalidate } = useSecurity();

  const [mode, setMode] = useState<"idle" | "disable" | "regenerate">("idle");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newCodes, setNewCodes] = useState<string[] | null>(null);

  const handleDisable = async () => {
    setError(null);
    setBusy(true);
    const result = await mfaApi.disableMfa(password, code);
    setBusy(false);
    if (result.ok) {
      invalidate();
      navigation.goBack();
    } else {
      setError(result.error.safeMessage);
    }
  };

  const handleRegenerate = async () => {
    setError(null);
    setBusy(true);
    const result = await mfaApi.regenerateBackupCodes(code);
    setBusy(false);
    if (result.ok) {
      setNewCodes(result.data.backup_codes);
      invalidate();
    } else {
      setError(result.error.safeMessage);
    }
  };

  if (isLoading || !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Two-step verification" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={200} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (newCodes) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="New recovery codes" onBack={() => navigation.goBack()} />
        <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="warning" title="Save these codes now" message="Your previous codes no longer work. These won't be shown again." />
          <View style={{ height: theme.spacing.base }} />
          <Card>{newCodes.map(c => <AppText key={c} variant="bodyStrong" style={{ fontFamily: "monospace", marginBottom: 4 }}>{c}</AppText>)}</Card>
          <View style={{ height: theme.spacing.base }} />
          <PrimaryButton label="Done" onPress={() => navigation.goBack()} fullWidth />
        </ScrollView>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Two-step verification" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <KeyValueList items={[
              { label: "Method", value: data.mfa.method === "totp" ? "Authenticator app" : "—" },
              { label: "Enabled since", value: formatDate(data.mfa.enabled_at) },
              { label: "Recovery codes left", value: data.mfa.recovery_codes_remaining != null ? String(data.mfa.recovery_codes_remaining) : "—" },
            ]} />
          </Card>
        </Section>

        {data.mfa.required_by_policy ? (
          <InlineAlert tone="neutral" title="Required by your organization" message="Your business requires two-step verification. It cannot be turned off from this app." />
        ) : error && mode === "idle" ? null : null}

        {mode === "idle" ? (
          <Section>
            <SecondaryButton label="Regenerate recovery codes" onPress={() => setMode("regenerate")} style={{ marginBottom: theme.spacing.sm }} fullWidth />
            {!data.mfa.required_by_policy ? (
              <DestructiveButton label="Disable two-step verification" onPress={() => setMode("disable")} fullWidth />
            ) : null}
          </Section>
        ) : mode === "regenerate" ? (
          <Section>
            <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.sm }}>Enter your current 6-digit code to generate new recovery codes. Old codes stop working immediately.</AppText>
            <PasswordField label="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />
            {error ? <View style={{ marginTop: theme.spacing.sm }}><InlineAlert tone="danger" title="Couldn't regenerate" message={error} /></View> : null}
            <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.base }}>
              <SecondaryButton label="Cancel" onPress={() => { setMode("idle"); setCode(""); setError(null); }} />
              <PrimaryButton label="Generate" onPress={handleRegenerate} loading={busy} disabled={code.length < 6} />
            </View>
          </Section>
        ) : (
          <Section>
            <AppText variant="bodySmall" color="tertiary" style={{ marginBottom: theme.spacing.sm }}>Enter your password and a current code to disable two-step verification.</AppText>
            <View style={{ marginBottom: theme.spacing.sm }}>
              <PasswordField label="Password" value={password} onChangeText={setPassword} />
            </View>
            <PasswordField label="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} />
            {error ? <View style={{ marginTop: theme.spacing.sm }}><InlineAlert tone="danger" title="Couldn't disable" message={error} /></View> : null}
            <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.base }}>
              <SecondaryButton label="Cancel" onPress={() => { setMode("idle"); setPassword(""); setCode(""); setError(null); }} />
              <DestructiveButton label="Disable" onPress={handleDisable} loading={busy} disabled={!password || code.length < 6} />
            </View>
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
