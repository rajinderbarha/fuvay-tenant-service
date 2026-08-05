import React from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { AppIconButton } from "../../components/AppIconButton";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { useConsentsQuery, useWithdrawConsentMutation } from "../../api/privacyData/usePrivacyDataQueries";
import { isConsentWithdrawable, ConsentRecord } from "../../domain/privacyData";
import { ServerTimestamp } from "../../domain/dates";

const CONSENT_LABELS: Record<string, string> = {
  marketing: "Marketing communications",
  location_access: "Location access",
  notification: "Notifications",
  profiling: "Personalization / profiling",
  ai_assistant_processing: "Assistant message processing",
  media_processing: "Media processing",
  terms_of_service: "Terms of service",
  privacy_policy: "Privacy policy acknowledgement",
};

/** Only the backend's own `WITHDRAWABLE_CONSENT_TYPES` ever render a
 * withdraw action -- required legal acknowledgements (terms, privacy
 * policy) are shown read-only, never behind a misleading toggle (spec
 * section 13). Latest record per consent_type wins (the list is
 * created_at-desc from the backend). */
export function PrivacyConsentScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const query = useConsentsQuery();
  const withdrawMutation = useWithdrawConsentMutation();

  if (query.isPending) {
    return <AppScreen><LoadingState label="Loading your consent choices…" /></AppScreen>;
  }
  if (query.isError && !query.data) {
    return <AppScreen><ErrorState title="We couldn't load your consent choices." actionLabel="Try again" onAction={() => query.refetch()} /></AppScreen>;
  }

  const latestByType = new Map<string, ConsentRecord>();
  for (const record of query.data ?? []) {
    if (!latestByType.has(record.consentType)) latestByType.set(record.consentType, record);
  }

  function confirmWithdraw(record: ConsentRecord) {
    const label = CONSENT_LABELS[record.consentType] ?? record.consentType;
    Alert.alert(
      `Withdraw ${label.toLowerCase()}?`,
      "You can change this again later.",
      [
        { text: "Keep it on", style: "cancel" },
        { text: "Withdraw", style: "destructive", onPress: () => withdrawMutation.mutate({ consentType: record.consentType }) },
      ],
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
          <AppIconButton name="chevron-back" onPress={() => navigation.goBack()} accessibilityLabel="Go back" />
          <View style={{ flex: 1 }}>
            <AppText variant="headingSmall" accessibilityRole="header">Privacy consent</AppText>
            <AppText variant="bodySmall" color="secondary">Review your current consent choices</AppText>
          </View>
        </View>

        <View style={{ gap: theme.spacing.sm }}>
          {Array.from(latestByType.values()).map(record => {
            const label = CONSENT_LABELS[record.consentType] ?? record.consentType;
            const withdrawable = isConsentWithdrawable(record.consentType);
            const active = record.action === "granted";
            return (
              <AppCard key={record.consentType} style={{ gap: theme.spacing.xxs }}>
                <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                  <AppText variant="bodyStrong">{label}</AppText>
                  <AppText variant="labelStrong" color={active ? "success" : "secondary"}>
                    {active ? "Active" : "Withdrawn"}
                  </AppText>
                </View>
                <AppText variant="caption" color="tertiary">Policy version {record.policyVersion}</AppText>
                {withdrawable && active ? (
                  <AppText
                    variant="labelStrong" color="danger" onPress={() => confirmWithdraw(record)}
                    accessibilityRole="button" accessibilityLabel={`Withdraw ${label}`}
                  >
                    Withdraw
                  </AppText>
                ) : !withdrawable ? (
                  <AppText variant="caption" color="tertiary">Required -- cannot be withdrawn while using Fuvay.</AppText>
                ) : null}
              </AppCard>
            );
          })}
          {latestByType.size === 0 ? (
            <AppText variant="bodySmall" color="secondary">No consent records found.</AppText>
          ) : null}
        </View>
      </View>
    </AppScreen>
  );
}
