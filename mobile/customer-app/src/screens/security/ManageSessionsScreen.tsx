import React, { useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { ManageSessionsHeader } from "../../components/manage-sessions/ManageSessionsHeader";
import { SessionsSummaryCard } from "../../components/manage-sessions/SessionsSummaryCard";
import { CurrentSessionCard } from "../../components/manage-sessions/CurrentSessionCard";
import { OtherSessionCard } from "../../components/manage-sessions/OtherSessionCard";
import { OtherSessionsEmptyState } from "../../components/manage-sessions/OtherSessionsEmptyState";
import { RevokeOtherDevicesFooter } from "../../components/manage-sessions/RevokeOtherDevicesFooter";
import { useCustomerSessionsQuery, useRevokeSessionMutation, useRevokeOtherSessionsMutation } from "../../api/customerSecurity/useCustomerSessionsQuery";
import { resolveSecurityCapabilities } from "../../domain/securityCapabilities";
import { isOffline } from "../../api/networkState";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "ManageSessions">;

/**
 * Opened from Security -> "Manage sessions". Every session shown and
 * every revoke performed is real (`GET /v1/auth/sessions`,
 * `DELETE /v1/auth/sessions/{id}`, `POST /v1/auth/sessions/revoke-all-
 * other`) -- no static device list, no local-only logout.
 */
export function ManageSessionsScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const sessionsQuery = useCustomerSessionsQuery();
  const revokeMutation = useRevokeSessionMutation();
  const revokeOthersMutation = useRevokeOtherSessionsMutation();
  const capabilities = resolveSecurityCapabilities();
  const [pendingRevokeId, setPendingRevokeId] = useState<string | null>(null);

  if (sessionsQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Checking active sessions…" />
      </AppScreen>
    );
  }

  if (sessionsQuery.isError && !sessionsQuery.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your sessions" actionLabel="Try again" onAction={() => sessionsQuery.refetch()} />
      </AppScreen>
    );
  }

  const sessions = sessionsQuery.data ?? [];
  const currentSession = sessions.find(s => s.isCurrent) ?? null;
  const otherSessions = sessions.filter(s => !s.isCurrent);
  const offline = isOffline();

  function handleRevoke(sessionId: string, deviceName: string | null) {
    Alert.alert(
      "Sign out this device?",
      `${deviceName ?? "This session"} will need to sign in again.`,
      [
        { text: "Keep session", style: "cancel" },
        {
          text: "Sign out", style: "destructive",
          onPress: async () => {
            if (revokeMutation.isPending) return;
            setPendingRevokeId(sessionId);
            try {
              await revokeMutation.mutateAsync(sessionId);
            } finally {
              setPendingRevokeId(null);
            }
          },
        },
      ],
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {offline && sessionsQuery.data ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <ManageSessionsHeader onBack={() => navigation.goBack()} />
        <SessionsSummaryCard activeCount={sessions.length} />

        {currentSession ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Current session</AppText>
            <CurrentSessionCard session={currentSession} />
          </View>
        ) : null}

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Other sessions</AppText>
          {otherSessions.length === 0 ? (
            <OtherSessionsEmptyState />
          ) : (
            otherSessions.map(session => (
              <OtherSessionCard
                key={session.sessionId}
                session={session}
                onSignOut={() => handleRevoke(session.sessionId, session.deviceName)}
                signingOut={pendingRevokeId === session.sessionId && revokeMutation.isPending}
              />
            ))
          )}
        </View>

        {capabilities.canRevokeOtherSessions && otherSessions.length > 0 ? (
          <RevokeOtherDevicesFooter
            onConfirm={() => revokeOthersMutation.mutate()}
            pending={revokeOthersMutation.isPending}
          />
        ) : null}

        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: theme.spacing.xxs }}>
          <AppText variant="caption" color="tertiary" align="center">Changed your password? Review sessions again.</AppText>
        </View>
      </View>
    </AppScreen>
  );
}
