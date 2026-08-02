import React from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { Switch } from "../../design-system/components/forms/Switch";
import { SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { usePrivacy } from "./usePrivacy";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { PrivacyStatusCode } from "../../services/privacy/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "PrivacyAndData">;

const STATUS_VISUAL: Record<PrivacyStatusCode, { icon: "lock-closed" | "alert-circle" | "time" | "help-circle"; color: "success" | "warning" | "tertiary" }> = {
  up_to_date: { icon: "lock-closed", color: "success" },
  request_in_progress: { icon: "time", color: "warning" },
  review_required: { icon: "alert-circle", color: "warning" },
  unavailable: { icon: "help-circle", color: "tertiary" },
};

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";

/**
 * Privacy & Data (Phase X). Extends the SAME canonical global DPDP/
 * compliance system used by customer and tenant requests -- this screen has
 * no local erasure/export logic, it only submits requests and displays the
 * backend's own lifecycle stage (spec section 1, 10).
 */
export function PrivacyAndDataScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const { summary, summaryLoading, summaryIsError, summaryError, refetchSummary, consents, consentsLoading, mutatingPurpose, mutationError, toggleConsent } = usePrivacy();

  if (summaryLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Privacy & data" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={500} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (summaryIsError && !summary) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Privacy & data" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load privacy settings" message={summaryError?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetchSummary()} />
      </SafeAreaScreen>
    );
  }

  if (!summary) return null;
  const visual = STATUS_VISUAL[summary.privacy_status.code];
  const recent = summary.recent_request;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Privacy & data" onBack={() => navigation.goBack()} />
      <ScrollView
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={refetchSummary} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached privacy settings. Requests and consent changes require a connection." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't save" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.base }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.brandPrimaryMuted }}>
              <Icon name="shield-outline" size="standard" color={theme.colors.brandPrimary} decorative />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Your privacy settings</AppText>
              <AppText variant="bodySmall" color="tertiary">Manage consent and requests connected to your ServiceOS account.</AppText>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: visual.color === "success" ? theme.colors.statusSuccessSurface : theme.colors.statusWarningSurface }}>
              <Icon name={visual.icon} size="compact" color={visual.color === "success" ? theme.colors.statusSuccess : theme.colors.statusWarning} decorative />
              <AppText variant="labelStrong" color={visual.color === "success" ? "success" : "warning"}>{summary.privacy_status.label}</AppText>
            </View>
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Consent" />
          <Card padding="base">
            {consentsLoading ? <Skeleton width="100%" height={140} radius={theme.radiusUsage.card} /> : consents.map(c => (
              <View key={c.purpose_code} style={{ paddingVertical: theme.spacing.sm }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <View style={{ flex: 1 }}>
                    <AppText variant="body">{c.label}</AppText>
                    <AppText variant="caption" color="tertiary">{c.description}</AppText>
                  </View>
                  {c.required ? (
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                      <Icon name="lock-closed" size="compact" color={theme.colors.textTertiary} decorative />
                      <AppText variant="labelStrong" color="tertiary">Required</AppText>
                    </View>
                  ) : (
                    <Switch
                      label="" value={c.enabled} onChange={(v) => toggleConsent(c.purpose_code, v)}
                      disabled={offline || mutatingPurpose === c.purpose_code}
                      accessibilityLabel={`${c.label}, ${c.enabled ? "on" : "off"}`}
                    />
                  )}
                </View>
              </View>
            ))}
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Your data" />
          <Card padding="base">
            <ListRow title="Data summary" subtitle="Profile, employment and activity records" trailing={<AppText variant="labelStrong" color="warning">View</AppText>} onPress={() => navigation.navigate("DataSummary")} />
            <ListRow title="Download my data" subtitle="Request a voluntary ServiceOS export" onPress={() => navigation.navigate("VoluntaryDataExport")} />
            <ListRow
              title="Privacy requests" subtitle="Access, correction, erasure and grievances"
              trailing={summary.request_counts.open > 0 ? <OpenPill count={summary.request_counts.open} /> : undefined}
              onPress={() => navigation.navigate("PrivacyRequestList")}
            />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Account" />
          <Card padding="base">
            <ListRow title="Account closure" subtitle="Request closure and relationship review" onPress={() => navigation.navigate("AccountClosureRequest")} />
            <ListRow title="Consent history" subtitle="Review when your choices changed" onPress={() => navigation.navigate("ConsentHistory")} />
          </Card>
        </Section>

        {recent ? (
          <Section>
            <SectionHeader title="Recent request" />
            <Card>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                <View style={{ flex: 1 }}>
                  <AppText variant="caption" color="tertiary">{recent.request_number}</AppText>
                  <AppText variant="bodyStrong">{requestTypeLabel(recent.request_type)}</AppText>
                  <View style={{ marginTop: theme.spacing.xs }}>
                    <View style={{ alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusWarningSurface }}>
                      <AppText variant="labelStrong" color="warning">{recent.status_label}</AppText>
                    </View>
                  </View>
                  <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
                    Submitted {formatDate(recent.submitted_at)} · Updated {formatDate(recent.updated_at)}
                  </AppText>
                </View>
                <SecondaryButton label="Track request" onPress={() => navigation.navigate("PrivacyRequestDetail", { requestId: recent.id })} />
              </View>
            </Card>
          </Section>
        ) : null}

        <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, backgroundColor: theme.colors.brandPrimaryMuted, borderRadius: theme.radiusUsage.card, marginTop: theme.spacing.base }}>
          <Icon name="information-circle" size="compact" color={theme.colors.brandPrimary} decorative />
          <AppText variant="bodySmall" style={{ flex: 1, color: theme.colors.brandPrimary }}>Privacy requests are reviewed across every ServiceOS category linked to your account.</AppText>
        </View>
        <AppText variant="caption" color="tertiary" style={{ textAlign: "center", marginTop: theme.spacing.base }}>
          Active jobs, disputes, finance records and legal retention may affect erasure or closure.
        </AppText>
      </ScrollView>
    </SafeAreaScreen>
  );
}

function OpenPill({ count }: { count: number }) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusWarningSurface }}>
      <AppText variant="labelStrong" color="warning">{count} open</AppText>
    </View>
  );
}

function requestTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    data_correction: "Correction request", consent_withdrawal: "Consent withdrawal",
    processing_objection: "Processing objection", grievance: "Grievance",
    staff_data_export: "Voluntary data export", staff_data_erasure: "Erasure / account closure",
  };
  return labels[type] ?? type;
}
