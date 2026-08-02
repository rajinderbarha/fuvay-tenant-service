import React from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useSecurity } from "./useSecurity";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { SecurityStatusDTO } from "../../services/auth/securityApi";

type Props = NativeStackScreenProps<ProfileStackParamList, "Security">;

const STATUS_VISUAL: Record<SecurityStatusDTO["level"], { icon: "shield-checkmark" | "shield-half" | "warning" | "help-circle"; color: "success" | "warning" | "danger" | "tertiary" }> = {
  protected: { icon: "shield-checkmark", color: "success" },
  protection_recommended: { icon: "shield-half", color: "warning" },
  action_required: { icon: "warning", color: "danger" },
  unavailable: { icon: "help-circle", color: "tertiary" },
};

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";
const formatDateTime = (iso: string) => new Date(iso).toLocaleString();

const ACTIVITY_LABEL: Record<string, string> = {
  "auth.login_success": "Successful sign-in",
  "auth.password_changed": "Password changed",
  "mfa.enabled": "MFA verified",
  "mfa.disabled": "MFA disabled",
  "device.trust_removed": "Trusted device removed",
  "device.trust_added": "Trusted device added",
  "session.revoked": "Session revoked",
};

/**
 * Security (Phase V). "Protected" is never shown just because the page
 * loaded -- every field here comes from the real backend security-overview
 * projection (spec section 3). Sensitive actions live on their own pushed
 * sub-screens; this hub is read-only navigation.
 */
export function SecurityScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const { data, isLoading, isError, error, isRefetching, refetch } = useSecurity();

  if (isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Security" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={400} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Security" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load security status" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;
  const visual = STATUS_VISUAL[data.security_status.level];

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Security" onBack={() => navigation.goBack()} />
      <ScrollView
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached security status. Security changes require a connection." /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.base }}>
            <View style={{ width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.statusSuccessSurface }}>
              <Icon name={visual.icon} size="standard" color={theme.colors.statusSuccess} decorative />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{data.security_status.label}</AppText>
              {data.security_status.reasons.length > 0 ? (
                <AppText variant="bodySmall" color="tertiary">
                  {data.security_status.reasons.length} recommendation{data.security_status.reasons.length === 1 ? "" : "s"} to improve your security
                </AppText>
              ) : (
                <AppText variant="bodySmall" color="tertiary">Password, MFA and trusted-device protection are active</AppText>
              )}
            </View>
            <View style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: 4, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusSuccessSurface }}>
              <AppText variant="labelStrong" color="success">{data.security_status.level === "protected" ? "Protected" : "Review"}</AppText>
            </View>
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Sign-in security" />
          <Card padding="base">
            <ListRow
              title="Password" subtitle={`Changed ${formatDate(data.password.changed_at)}`}
              trailing={<AppText variant="labelStrong" color="warning">Change</AppText>}
              onPress={() => navigation.navigate("ChangePassword")}
            />
            <ListRow
              title="Two-step verification" subtitle="Authenticator app"
              trailing={<StatusPill label={data.mfa.enabled ? "Enabled" : "Off"} tone={data.mfa.enabled ? "success" : "tertiary"} />}
              onPress={() => navigation.navigate(data.mfa.enabled ? "MFAManagement" : "MFASetup")}
            />
            <ListRow
              title="Trusted device" subtitle={data.current_device.device_name ?? "This device"}
              trailing={<StatusPill label={data.current_device.trusted ? "Trusted" : "Not trusted"} tone={data.current_device.trusted ? "success" : "tertiary"} />}
              onPress={() => navigation.navigate("TrustedDevice")}
            />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Verified contact" />
          <Card padding="base">
            <ListRow title="Mobile number" subtitle={data.verified_contacts.masked_mobile ?? "—"} trailing={data.verified_contacts.mobile_verified ? <StatusPill label="Verified" tone="success" icon="checkmark-circle" /> : null} />
            <ListRow title="Email address" subtitle={data.verified_contacts.masked_email ?? "—"} trailing={data.verified_contacts.email_verified ? <StatusPill label="Verified" tone="success" icon="checkmark-circle" /> : null} />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Sessions" />
          <Card padding="base">
            <ListRow
              title="Active sessions" subtitle={`${data.active_session_count} signed-in device${data.active_session_count === 1 ? "" : "s"}`}
              trailing={<AppText variant="labelStrong" color="warning">View</AppText>}
              onPress={() => navigation.navigate("ActiveSessions")}
            />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Recent security activity" />
          <Card padding="base">
            {data.recent_activity.length === 0 ? (
              <AppText variant="bodySmall" color="tertiary">No recent activity.</AppText>
            ) : data.recent_activity.slice(0, 3).map(item => (
              <View key={item.id} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: theme.spacing.sm }}>
                <View style={{ flex: 1 }}>
                  <AppText variant="body">{ACTIVITY_LABEL[item.action_type] ?? item.action_type}</AppText>
                  <AppText variant="caption" color="tertiary">{item.outcome === "success" ? "This device" : item.failure_reason ?? item.outcome}</AppText>
                </View>
                <AppText variant="caption" color="tertiary">{formatDateTime(item.created_at)}</AppText>
              </View>
            ))}
          </Card>
          <View style={{ marginTop: theme.spacing.sm }}>
            <ListRow title="Review security activity" onPress={() => navigation.navigate("SecurityActivity")} trailing={<Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimary} decorative />} />
          </View>
        </Section>

        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, padding: theme.spacing.base }}>
          <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>ServiceOS will never ask for your password or OTP.</AppText>
        </View>
      </ScrollView>
    </SafeAreaScreen>
  );
}

function StatusPill({ label, tone, icon }: { label: string; tone: "success" | "tertiary"; icon?: "checkmark-circle" }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: tone === "success" ? theme.colors.statusSuccessSurface : theme.colors.statusNeutralSurface }}>
      {icon ? <Icon name={icon} size="compact" color={theme.colors.statusSuccess} decorative /> : null}
      <AppText variant="labelStrong" color={tone}>{label}</AppText>
    </View>
  );
}
