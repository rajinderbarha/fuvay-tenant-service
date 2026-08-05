import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { AppCard } from "../../components/AppCard";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { SecurityHeader } from "../../components/security/SecurityHeader";
import { SecurityInfoPanel } from "../../components/security/SecurityInfoPanel";
import { MobileNumberRow } from "../../components/security/MobileNumberRow";
import { PasswordRow } from "../../components/security/PasswordRow";
import { ChangePasswordCard } from "../../components/security/ChangePasswordCard";
import { TwoStepRow } from "../../components/security/TwoStepRow";
import { ThisDeviceRow } from "../../components/security/ThisDeviceRow";
import { GlobalSignOutRow } from "../../components/security/GlobalSignOutRow";
import { useCustomerProfileQuery } from "../../api/customer/useCustomerProfileQuery";
import { useCustomerSessionsQuery } from "../../api/customerSecurity/useCustomerSessionsQuery";
import { useGlobalLogoutMutation } from "../../api/customerSecurity/useGlobalLogoutMutation";
import { resolveSecurityCapabilities } from "../../domain/securityCapabilities";
import { isOffline } from "../../api/networkState";
import { logout } from "../../api/session/sessionManager";

/**
 * Opened from Profile -> "Security". No bottom navigation (focused
 * stack screen, spec section 4). All rows are gated by
 * `resolveSecurityCapabilities()` -- an unsupported action is hidden
 * entirely, never a decorative row (spec section 3).
 */
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "Security">;

export function SecurityScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const profileQuery = useCustomerProfileQuery();
  const sessionsQuery = useCustomerSessionsQuery();
  const globalLogoutMutation = useGlobalLogoutMutation();
  const capabilities = resolveSecurityCapabilities();

  const [changingPassword, setChangingPassword] = useState(false);

  if (profileQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading security settings" />
      </AppScreen>
    );
  }

  if (profileQuery.isError && !profileQuery.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your security settings" actionLabel="Try again" onAction={() => profileQuery.refetch()} />
      </AppScreen>
    );
  }

  const profile = profileQuery.data;
  const currentSession = (sessionsQuery.data ?? []).find(s => s.isCurrent);

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {isOffline() ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <SecurityHeader onBack={() => navigation.goBack()} />
        <SecurityInfoPanel />

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Sign-in & verification</AppText>
          <AppCard style={{ gap: theme.spacing.xs }}>
            {profile ? <MobileNumberRow phone={profile.phone} verified={profile.verified} /> : null}

            {capabilities.canChangePassword ? (
              changingPassword ? (
                <ChangePasswordCard onDone={() => setChangingPassword(false)} onCancel={() => setChangingPassword(false)} />
              ) : (
                <PasswordRow onChange={() => setChangingPassword(true)} />
              )
            ) : null}

            {profile ? (
              <TwoStepRow
                enabled={profile.mfaEnabled}
                canSetup={capabilities.canSetupMfa}
                canDisable={capabilities.canDisableMfa}
                onSetup={() => navigation.navigate("MfaManage")}
                onManage={() => navigation.navigate("MfaManage")}
              />
            ) : null}
          </AppCard>
        </View>

        {capabilities.canListSessions ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Signed-in sessions</AppText>
            <AppCard style={{ gap: theme.spacing.xs }}>
              {sessionsQuery.isPending ? (
                <LoadingState label="Loading sessions" />
              ) : (
                <ThisDeviceRow isCurrent={!!currentSession} />
              )}
              {capabilities.canManageSessions ? (
                <AppText
                  variant="labelStrong" color="link"
                  onPress={() => navigation.navigate("ManageSessions")}
                  accessibilityRole="button" accessibilityLabel="Manage sessions"
                >
                  Manage sessions
                </AppText>
              ) : null}
            </AppCard>
          </View>
        ) : null}

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Account access</AppText>
          <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">Login activity</AppText>
              <AppText variant="bodySmall" color="secondary">Review recent sign-ins to your account</AppText>
            </View>
            <AppText
              variant="labelStrong" color="link"
              onPress={() => navigation.navigate("LoginActivity")}
              accessibilityRole="button" accessibilityLabel="Login activity"
            >
              View
            </AppText>
          </AppCard>
          {capabilities.canRequestPasswordReset ? (
            <AppCard style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
              <View style={{ flex: 1 }}>
                <AppText variant="bodyStrong">Forgot password?</AppText>
                <AppText variant="bodySmall" color="secondary">Sign out to verify your identity and reset it</AppText>
              </View>
              <AppText
                variant="labelStrong" color="link"
                onPress={() => logout()}
                accessibilityRole="button" accessibilityLabel="Sign out to reset your password"
              >
                Reset
              </AppText>
            </AppCard>
          ) : null}

          {capabilities.canGlobalLogout ? (
            <GlobalSignOutRow onConfirm={() => globalLogoutMutation.mutate()} pending={globalLogoutMutation.isPending} />
          ) : null}
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <AppText variant="caption" color="tertiary" align="center">Fuvay will never ask for your password or OTP.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
