import React from "react";
import { View, ScrollView, RefreshControl, Pressable } from "react-native";
import Constants from "expo-constants";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, ListRow, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { SecondaryButton, PrimaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useHelpWorkspace } from "./useHelpWorkspace";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { ServiceStatusDTO } from "../../services/support/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "HelpAndSupport">;

const STATUS_VISUAL: Record<ServiceStatusDTO["state"], { color: string; label: string }> = {
  operational: { color: "success", label: "All systems operational" } as any,
  degraded: { color: "warning", label: "Partial disruption" } as any,
  major_incident: { color: "danger", label: "Major disruption" } as any,
  maintenance: { color: "warning", label: "Scheduled maintenance" } as any,
  unavailable: { color: "tertiary", label: "Status unavailable" } as any,
};

const formatRelative = (iso: string) => {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleDateString();
};

/**
 * Help & Support (Phase Y). Reuses the EXISTING real Tenant Help & Support
 * engine end-to-end -- no fake contact buttons, no fabricated chat, no
 * static request list. Support ownership is guided, not assumed: job/
 * schedule/employment issues route to your manager; app/account/security
 * issues route to ServiceOS platform support (spec section 1, 9).
 */
export function HelpAndSupportScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const { data, isLoading, isError, error, isRefetching, refetch, manager } = useHelpWorkspace();

  if (isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Help & support" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={500} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Help & support" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load help & support" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;
  const statusVisual = STATUS_VISUAL[data.service_status.state];
  const recent = data.requests[0];
  const appVersion = Constants.expoConfig?.version ?? "1.0.0";

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Help & support" onBack={() => navigation.goBack()} />
      <ScrollView
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached help & support. New requests require a connection." /></View> : null}

        <Section>
          <Pressable onPress={() => navigation.navigate("HelpSearch")} accessibilityRole="search">
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm, borderRadius: theme.radiusUsage.card, borderWidth: 1, borderColor: theme.colors.borderDefault, backgroundColor: theme.colors.surfaceInteractive }}>
              <Icon name="search" size="compact" color={theme.colors.textTertiary} decorative />
              <AppText variant="body" color="tertiary">Search help articles</AppText>
            </View>
          </Pressable>
        </Section>

        <Section>
          <Card style={{ flexDirection: "row", gap: theme.spacing.base }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.brandPrimaryMuted }}>
              <Icon name="headset-outline" size="standard" color={theme.colors.brandPrimary} decorative />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">How can we help?</AppText>
              <AppText variant="bodySmall" color="tertiary">Find answers or contact the right support team.</AppText>
            </View>
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Quick help" />
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
            {/* Matches the reference design's 4 tiles. The real backend's
                product_area taxonomy (app/engines/support/constants.py) has
                no distinct "Schedule & leave" area -- that tile reuses the
                real "bookings_jobs" area (schedule/leave articles are
                seeded there too, migration 218) rather than fabricating a
                new, unregistered category key. */}
            {[
              { areaKey: "bookings_jobs", label: "Job execution", description: "Inspection, estimates & completion", icon: "construct-outline" as const },
              { areaKey: "bookings_jobs", label: "Schedule & leave", description: "Availability and time off", icon: "calendar-outline" as const },
              { areaKey: "account_security", label: "Account & security", description: "Login, MFA and sessions", icon: "shield-checkmark-outline" as const },
              { areaKey: "team_access", label: "Documents", description: "Uploads, review and expiry", icon: "document-text-outline" as const },
            ].map(tile => (
              <View key={tile.label} style={{ width: "47%" }}>
                <Card padding="base" onTouchEnd={() => navigation.navigate("HelpCategory", { areaKey: tile.areaKey, areaLabel: tile.label })}>
                  <Icon name={tile.icon} size="standard" color={theme.colors.brandPrimary} decorative />
                  <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.xs }}>{tile.label}</AppText>
                  <AppText variant="caption" color="tertiary">{tile.description}</AppText>
                </Card>
              </View>
            ))}
          </View>
        </Section>

        <Section>
          <SectionHeader title="Contact support" />
          <Card padding="base">
            <ListRow
              title="Contact your manager"
              subtitle="Assignments, schedule and employment"
              trailing={manager?.display_name ? <AppText variant="caption" color="tertiary">{manager.display_name}</AppText> : undefined}
              onPress={() => navigation.navigate("CreateSupportRequest", { intent: "manager" })}
            />
            <ListRow title="ServiceOS support" subtitle="App, account or platform issue" onPress={() => navigation.navigate("CreateSupportRequest", { intent: "platform" })} />
            <ListRow title="Report a technical problem" subtitle="Send safe diagnostics with your report" onPress={() => navigation.navigate("CreateSupportRequest", { intent: "technical" })} />
          </Card>
        </Section>

        {recent ? (
          <Section>
            <SectionHeader title="Your requests" />
            <Card>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <View style={{ flex: 1 }}>
                  <AppText variant="caption" color="tertiary">{recent.ticket_number}</AppText>
                  <AppText variant="bodyStrong">{recent.subject}</AppText>
                  <AppText variant="caption" color="tertiary">Updated {formatRelative(recent.updated_at)}</AppText>
                </View>
                <View style={{ alignItems: "flex-end", gap: theme.spacing.xs }}>
                  <View style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusInfoSurface }}>
                    <AppText variant="labelStrong" color="info">{recent.status_label}</AppText>
                  </View>
                  <SecondaryButton label="View request" onPress={() => navigation.navigate("SupportRequestDetail", { requestId: recent.id })} />
                </View>
              </View>
            </Card>
          </Section>
        ) : null}

        <Section>
          <SectionHeader title="App information" />
          <Card padding="base">
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: theme.spacing.xs }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
                <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: (statusVisual.color as any) === "success" ? theme.colors.statusSuccess : theme.colors.statusWarning }} />
                <AppText variant="body">Service status</AppText>
              </View>
              <AppText variant="bodySmall" color={statusVisual.color as any}>{statusVisual.label}</AppText>
            </View>
            <KeyValueList items={[{ label: "App version", value: `${appVersion} (${Constants.expoConfig?.ios?.buildNumber ?? Constants.expoConfig?.android?.versionCode ?? "1"})` }]} />
            <ListRow title="Privacy & terms" onPress={() => navigation.navigate("PrivacyAndData")} />
          </Card>
        </Section>

        <PrimaryButton label="Create support request" onPress={() => navigation.navigate("CreateSupportRequest")} fullWidth />
        <AppText variant="caption" color="tertiary" style={{ textAlign: "center", marginTop: theme.spacing.base }}>
          For emergencies, contact local emergency services.{"\n"}ServiceOS support is not an emergency service.
        </AppText>
      </ScrollView>
    </SafeAreaScreen>
  );
}
