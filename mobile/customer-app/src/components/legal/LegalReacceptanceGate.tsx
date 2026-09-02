import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  acceptLegalDocuments,
  getLegalConsentStatus,
  LegalConsentStatus,
} from "../../api/legalDocuments/legalDocumentsApi";
import { useTheme } from "../../design-system/theme";
import { AppButton } from "../AppButton";
import { AppText } from "../AppText";

export function LegalReacceptanceGate({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  const [status, setStatus] = useState<LegalConsentStatus | null>(null);
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await getLegalConsentStatus());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't check the updated terms.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function accept() {
    if (!status || !checked) return;
    setSaving(true);
    setError(null);
    try {
      setStatus(await acceptLegalDocuments(status.document_ids));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't save your acceptance.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.backgroundPrimary }}>
        <ActivityIndicator color={theme.colors.brandPrimary} />
        <AppText color="secondary" style={{ marginTop: theme.spacing.sm }}>Checking updated terms…</AppText>
      </SafeAreaView>
    );
  }
  if (error && !status) {
    return (
      <SafeAreaView style={{ flex: 1, padding: theme.spacing.lg, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.backgroundPrimary }}>
        <AppText variant="title" align="center">We couldn&apos;t check the updated terms</AppText>
        <AppText color="danger" align="center" style={{ marginVertical: theme.spacing.base }}>{error}</AppText>
        <AppButton label="Try again" onPress={load} />
      </SafeAreaView>
    );
  }
  if (!status?.requires_acceptance) return <>{children}</>;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.base }}>
        <AppText color="link" variant="caption">ACTION REQUIRED</AppText>
        <AppText variant="display">Review our updated service terms</AppText>
        <AppText color="secondary">{status.message}</AppText>

        <View style={{ padding: theme.spacing.base, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceSecondary, gap: theme.spacing.sm }}>
          <AppText>• Your provider is responsible for technician screening, supervision, and field work.</AppText>
          <AppText>• Warranty, complaint, refund, and settlement decisions are handled directly with the provider.</AppText>
          <AppText>• ServiceOS does not hold a provider security deposit or adjudicate the case.</AppText>
          <AppText>• Missed response SLAs may affect provider credits, health, and bookability.</AppText>
        </View>

        {status.documents.map(document => (
          <View key={document.id} style={{ paddingVertical: theme.spacing.sm }}>
            <AppText variant="title">{document.title} · v{document.version}</AppText>
            {document.summary ? <AppText color="secondary" style={{ marginTop: theme.spacing.xs }}>{document.summary}</AppText> : null}
            <AppText color="secondary" style={{ marginTop: theme.spacing.sm }}>{document.body}</AppText>
          </View>
        ))}

        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked }}
          onPress={() => setChecked(value => !value)}
          style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, padding: theme.spacing.base, borderWidth: 1, borderColor: checked ? theme.colors.brandPrimary : theme.colors.borderDefault, borderRadius: theme.radiusUsage.card }}
        >
          <View style={{ width: 22, height: 22, borderRadius: 5, alignItems: "center", justifyContent: "center", backgroundColor: checked ? theme.colors.brandPrimary : theme.colors.surfaceDefault }}>
            {checked ? <AppText color="inverse">✓</AppText> : null}
          </View>
          <AppText style={{ flex: 1 }}>I have read and accept these updated terms.</AppText>
        </Pressable>
        {error ? <AppText color="danger" accessibilityRole="alert">{error}</AppText> : null}
        <AppButton
          label="Accept and continue"
          onPress={accept}
          disabled={!checked}
          disabledReason="Read and select the acceptance checkbox first."
          loading={saving}
          fullWidth
        />
      </ScrollView>
    </SafeAreaView>
  );
}
