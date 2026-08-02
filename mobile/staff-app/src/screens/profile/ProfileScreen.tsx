import React, { useCallback } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Heading } from "../../design-system/components/typography/Heading";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { ListRow, SectionHeader } from "../../design-system/components/data-display/InfoRow";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { DestructiveButton } from "../../design-system/components/actions/Buttons";
import { ConfirmationDialog } from "../../design-system/components/overlays/ConfirmationDialog";
import { IdentityCard } from "./components/IdentityCard";
import { ReadinessStrip } from "./components/ReadinessStrip";
import { useProfile } from "./useProfile";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { revokeCurrentSession } from "../../services/auth/sessionManager";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import Constants from "expo-constants";

type Props = NativeStackScreenProps<ProfileStackParamList, "ProfileHome">;

/**
 * Profile & Account Hub (Phase R). Tenant/platform-controlled fields are
 * displayed read-only throughout -- this screen never silently accepts an
 * edit to a field the backend would reject (spec section 4).
 */
export function ProfileScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const [signOutOpen, setSignOutOpen] = React.useState(false);
  const [signingOut, setSigningOut] = React.useState(false);

  const { data, isLoading, isError, error, isRefetching, refetch } = useProfile();

  const handleSignOut = useCallback(async () => {
    setSigningOut(true);
    await revokeCurrentSession();
    // SessionProvider listens for SESSION_CLEARED and resets navigation to
    // the auth stack automatically -- no manual navigation here (spec
    // section 15: prevent authenticated back navigation).
  }, []);

  if (isLoading) {
    return (
      <SafeAreaScreen style={{ padding: theme.spacing.lg }}>
        <Skeleton width="40%" height={24} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={120} radius={theme.radiusUsage.card} />
        <View style={{ height: theme.spacing.base }} />
        <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load your profile" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  return (
    <SafeAreaScreen style={{ flex: 1, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.base }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.base }}>
        <Heading level="large">Profile</Heading>
        <IconButton icon="settings-outline" accessibilityLabel="Settings" onPress={() => {}} />
      </View>

      <ScrollView
        contentContainerStyle={{ paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached profile data." /></View> : null}

        <Section>
          <IdentityCard identity={data.identity} employment={data.employment} onEdit={() => navigation.navigate("EditPersonalProfile")} />
        </Section>

        <Section>
          <Card>
            <ReadinessStrip readiness={data.readiness} />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Work account" />
          <Card padding="base">
            <ListRow title="Employment details" subtitle="Role, services and skills" trailing={<AppText variant="caption" color="tertiary">Read-only</AppText>} onPress={() => navigation.navigate("EmploymentDetails")} />
            <ListRow title="Documents" subtitle="Identity and certification" trailing={data.readiness.missing.some(m => m.code === "DOCUMENTS_INCOMPLETE") ? <AppText variant="caption" color="warning">Incomplete</AppText> : undefined} onPress={() => navigation.navigate("Documents")} />
            <ListRow title="Availability preferences" subtitle="Working pattern and service radius" onPress={() => navigation.navigate("AvailabilityPreferences")} />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Preferences" />
          <Card padding="base">
            <ListRow title="Notifications" subtitle="Push and alert preferences" onPress={() => navigation.navigate("NotificationPreferences")} />
            <ListRow title="Appearance" subtitle="System theme" onPress={() => navigation.navigate("Appearance")} />
          </Card>
        </Section>

        <Section>
          <SectionHeader title="Security & support" />
          <Card padding="base">
            <ListRow title="Security" subtitle="Password, MFA and trusted device" trailing={data.security.mfa_enabled ? <AppText variant="caption" color="success">Protected</AppText> : undefined} onPress={() => navigation.navigate("Security")} />
            <ListRow title="Active sessions" subtitle={`${data.security.active_session_count} signed-in device${data.security.active_session_count === 1 ? "" : "s"}`} onPress={() => navigation.navigate("ActiveSessions")} />
            <ListRow title="Privacy & data" subtitle="Consent and account requests" onPress={() => navigation.navigate("PrivacyAndData")} />
            <ListRow title="Help & support" subtitle="Guides and contact support" onPress={() => navigation.navigate("HelpAndSupport")} />
          </Card>
        </Section>

        <DestructiveButton label="Sign out" onPress={() => setSignOutOpen(true)} fullWidth />
        <AppText variant="caption" color="tertiary" style={{ textAlign: "center", marginTop: theme.spacing.sm }}>
          ServiceOS Staff · v{Constants.expoConfig?.version ?? "1.0.0"}
        </AppText>
      </ScrollView>

      <ConfirmationDialog
        visible={signOutOpen}
        title="Sign out?"
        message="You'll need to sign in again to access your jobs and schedule."
        confirmLabel="Sign out"
        destructive
        loading={signingOut}
        onConfirm={handleSignOut}
        onCancel={() => setSignOutOpen(false)}
      />
    </SafeAreaScreen>
  );
}
