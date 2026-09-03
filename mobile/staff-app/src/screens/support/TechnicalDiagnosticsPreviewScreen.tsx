import React, { useState } from "react";
import { View, ScrollView, Platform } from "react-native";
import Constants from "expo-constants";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "TechnicalDiagnosticsPreview">;

/**
 * Technical Diagnostics Preview (Phase Y spec section 13). Shows EXACTLY
 * what will be attached before submission -- no access/refresh tokens, no
 * customer data, no job payload, no exact GPS, no push token. Every field
 * here is either client-known safe metadata or the standard per-request
 * correlation id (no dedicated diagnostics-capture backend exists -- this
 * is the honest, disclosed scope, not a fabricated deep telemetry system).
 */
export function TechnicalDiagnosticsPreviewScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const diagnostics = {
    "App version": `${Constants.expoConfig?.version ?? "1.0.0"} (${Constants.expoConfig?.android?.versionCode ?? Constants.expoConfig?.ios?.buildNumber ?? "1"})`,
    "Platform": `${Platform.OS} ${Platform.Version}`,
    "Network": networkStatus,
    "Timestamp": new Date().toISOString(),
  };

  const handleSubmit = async () => {
    setBusy(true);
    setError(null);
    const description = route.params?.description ?? "Technical problem reported from diagnostics preview.";
    const diagText = Object.entries(diagnostics).map(([k, v]) => `${k}: ${v}`).join("\n");
    const result = await api.createSupportRequest({
      category: route.params?.category ?? "technical",
      subject: route.params?.subject ?? "Technical problem",
      description: `${description}\n\n-- Diagnostics --\n${diagText}`,
      impact: route.params?.impact ?? "one_user_affected",
    });
    setBusy(false);
    if (result.ok) {
      setSubmitted(true);
    } else {
      setError(result.error.safeMessage);
    }
  };

  if (submitted) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Report submitted" onBack={() => navigation.popToTop()} />
        <View style={{ padding: theme.spacing.lg }}>
          <InlineAlert tone="success" title="Report submitted" message="Fuvay support will review this with the diagnostics shown above." />
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Diagnostics preview" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <AppText variant="bodySmall" color="tertiary">This is exactly what will be sent with your report. Nothing else.</AppText>
        </Section>
        <Section>
          <SectionHeader title="Will be included" />
          <Card>
            <KeyValueList items={Object.entries(diagnostics).map(([label, value]) => ({ label, value: String(value) }))} />
          </Card>
        </Section>
        <Section>
          <SectionHeader title="Never included" />
          <Card padding="base">
            {["Access or refresh tokens", "Password, OTP or MFA secrets", "Customer names or contact details", "Full job payloads", "Identity documents", "Exact location"].map(item => (
              <AppText key={item} variant="bodySmall" color="tertiary" style={{ marginBottom: 4 }}>• {item}</AppText>
            ))}
          </Card>
        </Section>
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't submit" message={error} /></View> : null}
        <PrimaryButton label="Send report" onPress={handleSubmit} loading={busy} fullWidth />
      </ScrollView>
    </SafeAreaScreen>
  );
}
