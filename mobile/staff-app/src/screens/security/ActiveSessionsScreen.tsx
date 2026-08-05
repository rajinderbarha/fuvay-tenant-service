import React, { useCallback, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { ListRow } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { SecondaryButton, DestructiveButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import { ConfirmationDialog as ConfirmDialog } from "../../design-system/components/overlays/ConfirmationDialog";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import * as authApi from "../../services/auth/authApi";
import * as securityApi from "../../services/auth/securityApi";
import { SessionListItemDTO } from "../../services/auth/types";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "ActiveSessions">;

const formatRelative = (iso?: string | null) => {
  if (!iso) return "Unknown";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "Active now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
};
const formatSignedIn = (iso?: string | null) => iso ? `Signed in ${new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })}` : null;

/**
 * Active Sessions & Devices (Phase W). `current_session_id` is resolved
 * SERVER-SIDE from the authenticated JWT (spec section 7) -- this screen
 * never guesses; if resolution fails (no session marked current), bulk
 * sign-out and per-row trust actions are disabled rather than assumed safe.
 */
export function ActiveSessionsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [confirmRevokeId, setConfirmRevokeId] = useState<string | null>(null);
  const [confirmRevokeAll, setConfirmRevokeAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removingTrust, setRemovingTrust] = useState(false);

  const query = useQuery({
    queryKey: ["active-sessions"],
    queryFn: async () => {
      const result = await authApi.listSessions();
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const handleRevoke = useCallback(async (sessionId: string) => {
    setError(null);
    setRevokingId(sessionId);
    const result = await authApi.revokeSession(sessionId);
    setRevokingId(null);
    setConfirmRevokeId(null);
    if (result.ok) queryClient.invalidateQueries({ queryKey: ["active-sessions"] });
    else setError(result.error.safeMessage);
  }, [queryClient]);

  const handleRevokeAll = useCallback(async () => {
    setConfirmRevokeAll(false);
    setError(null);
    const result = await authApi.revokeAllOtherSessions();
    if (result.ok) queryClient.invalidateQueries({ queryKey: ["active-sessions"] });
    else setError(result.error.safeMessage);
  }, [queryClient]);

  const handleRemoveTrust = useCallback(async (sessionId: string) => {
    setRemovingTrust(true);
    setError(null);
    const result = await securityApi.removeDeviceTrust(sessionId);
    setRemovingTrust(false);
    if (result.ok) queryClient.invalidateQueries({ queryKey: ["active-sessions"] });
    else setError(result.error.safeMessage);
  }, [queryClient]);

  if (query.isLoading) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Active sessions" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><Skeleton width="100%" height={400} radius={theme.radiusUsage.card} /></View>
      </SafeAreaScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Active sessions" onBack={() => navigation.goBack()} />
        <ErrorState icon="cloud-offline-outline" title="Couldn't load sessions" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
      </SafeAreaScreen>
    );
  }

  const data = query.data;
  if (!data) return null;

  const sessions = data.sessions;
  const currentSession = sessions.find(s => s.session_id === data.current_session_id);
  const otherSessions = sessions.filter(s => s.session_id !== data.current_session_id);
  // Fail-safe: if the backend couldn't resolve a current session, never guess
  // -- disable the bulk action rather than assume every row is "other".
  const currentSessionResolved = !!data.current_session_id;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Active sessions" onBack={() => navigation.goBack()} />
      <ScrollView
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={query.refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Showing cached sessions. Sign-out and trust actions require a connection." /></View> : null}
        {error ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete action" message={error} /></View> : null}
        {!currentSessionResolved ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="warning" title="Current device unknown" message="We couldn't confirm which session is this device -- bulk sign-out is disabled for safety." /></View> : null}

        <Section>
          <Card style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.base }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.brandPrimaryMuted }}>
              <Icon name="shield-outline" size="standard" color={theme.colors.brandPrimary} decorative />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{sessions.length} signed-in device{sessions.length === 1 ? "" : "s"}</AppText>
              <AppText variant="bodySmall" color="tertiary">Review devices that can access your account.</AppText>
            </View>
          </Card>
        </Section>

        {currentSession ? (
          <Section>
            <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>Current device</AppText>
            <SessionCard
              session={currentSession}
              isCurrent
              offline={offline}
              onRemoveTrust={() => handleRemoveTrust(currentSession.session_id)}
              removingTrust={removingTrust}
            />
          </Section>
        ) : null}

        {otherSessions.length > 0 ? (
          <Section>
            <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>Other sessions</AppText>
            {otherSessions.map(session => (
              <SessionCard
                key={session.session_id}
                session={session}
                isCurrent={false}
                offline={offline}
                onSignOut={() => setConfirmRevokeId(session.session_id)}
                signingOut={revokingId === session.session_id}
              />
            ))}
          </Section>
        ) : sessions.length <= 1 ? (
          <Section><EmptyState icon="phone-portrait-outline" title="No other sessions" message="You're only signed in on this device." /></Section>
        ) : null}

        <Section>
          <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>Device trust</AppText>
          <Card padding="base">
            <ListRow
              title="Trusted devices" subtitle="Trusted devices may require fewer MFA checks. Trust never changes job permissions."
              trailing={<AppText variant="labelStrong">{data.trusted_device_count}</AppText>}
            />
          </Card>
        </Section>

        <DestructiveButton
          label="Sign out all other sessions"
          onPress={() => setConfirmRevokeAll(true)}
          disabled={offline || !currentSessionResolved || otherSessions.length === 0}
          fullWidth
        />

        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, marginTop: theme.spacing.base }}>
          <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>Session changes are recorded in your security activity.</AppText>
        </View>
      </ScrollView>

      <ConfirmDialog
        visible={!!confirmRevokeId}
        title="Sign out this device?"
        message="This device will need to sign in again to access your account."
        confirmLabel="Sign out"
        destructive
        loading={!!revokingId}
        onConfirm={() => confirmRevokeId && handleRevoke(confirmRevokeId)}
        onCancel={() => setConfirmRevokeId(null)}
      />
      <ConfirmDialog
        visible={confirmRevokeAll}
        title="Sign out all other devices?"
        message={`This will end access on every other signed-in device. You will remain signed in on this device.${otherSessions.length ? ` ${otherSessions.length} device${otherSessions.length === 1 ? "" : "s"} affected.` : ""}`}
        confirmLabel="Sign out devices"
        destructive
        onConfirm={handleRevokeAll}
        onCancel={() => setConfirmRevokeAll(false)}
      />
    </SafeAreaScreen>
  );
}

function SessionCard({ session, isCurrent, offline, onSignOut, signingOut, onRemoveTrust, removingTrust }: {
  session: SessionListItemDTO; isCurrent: boolean; offline: boolean;
  onSignOut?: () => void; signingOut?: boolean;
  onRemoveTrust?: () => void; removingTrust?: boolean;
}) {
  const { theme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const displayName = session.device_display_name ?? session.device_name ?? "Unknown device";
  const signedInLabel = formatSignedIn(session.created_at);

  return (
    <Card style={{ marginBottom: theme.spacing.sm, borderWidth: isCurrent ? 1 : 0, borderColor: theme.colors.statusSuccess }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">{displayName}</AppText>
          <View style={{ flexDirection: "row", gap: 6, marginTop: theme.spacing.xs, flexWrap: "wrap" }}>
            {isCurrent ? <Pill label="This device" tone="success" /> : null}
            <Pill label={session.is_trusted ? "Trusted" : "Not trusted"} tone={session.is_trusted ? "success" : "neutral"} />
          </View>
          {session.device_type ? <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>{session.device_type}</AppText> : null}
          <AppText variant="caption" color="tertiary">
            {session.approximate_location ?? "Location unavailable"} · <AppText variant="caption" color={isCurrent ? "success" : "tertiary"}>{formatRelative(session.last_active_at)}</AppText>
          </AppText>
          {signedInLabel ? <AppText variant="caption" color="tertiary">{signedInLabel}</AppText> : null}
        </View>
        {isCurrent ? (
          <IconButton icon="ellipsis-vertical" accessibilityLabel="Device options" onPress={() => setMenuOpen(v => !v)} />
        ) : (
          <SecondaryButton label="Sign out" onPress={onSignOut ?? (() => {})} loading={signingOut} disabled={offline} />
        )}
      </View>
      {isCurrent && menuOpen ? (
        <View style={{ marginTop: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.sm }}>
          <ListRow title="Remove trust" onPress={() => { setMenuOpen(false); onRemoveTrust?.(); }} />
        </View>
      ) : null}
    </Card>
  );
}

function Pill({ label, tone }: { label: string; tone: "success" | "neutral" }) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: tone === "success" ? theme.colors.statusSuccessSurface : theme.colors.statusNeutralSurface }}>
      <AppText variant="labelStrong" color={tone === "success" ? "success" : "tertiary"}>{label}</AppText>
    </View>
  );
}
