import React, { useState } from "react";
import { View } from "react-native";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { Section } from "../../../components/layout/Section";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppBadge } from "../../../components/primitives/AppBadge";
import { LoadingIndicator } from "../../../components/feedback/LoadingIndicator";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { ConfirmationModal } from "../../../components/feedback/ConfirmationModal";
import { toastService } from "../../../components/feedback/toast-service";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useSessions, useRevokeSession } from "../queries/session-queries";
import { useLogoutAll } from "../hooks/use-logout-all";
import type { ValidatedSessionSummary } from "../domain/session-summary-schema";

/**
 * CUSTOMER-L5-02 §37/§36 — real GET/DELETE /v1/auth/sessions and
 * POST /v1/auth/logout-all. Ownership is enforced server-side
 * (service.py#revoke_session rejects a session that doesn't belong to the
 * requesting user) — this screen never displays or accepts a raw token.
 */
export function SessionsScreen() {
  const { theme } = useAppTheme();
  const sessions = useSessions();
  const revokeSession = useRevokeSession();
  const { logoutAll, loading: loggingOutAll } = useLogoutAll();
  const [confirmingLogoutAll, setConfirmingLogoutAll] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  async function handleRevoke(session: ValidatedSessionSummary) {
    setRevokingId(session.session_id);
    try {
      await revokeSession.mutateAsync(session.session_id);
      toastService.success("Session signed out");
    } catch {
      toastService.error("Couldn't sign out that session");
    } finally {
      setRevokingId(null);
    }
  }

  async function handleConfirmLogoutAll() {
    setConfirmingLogoutAll(false);
    const result = await logoutAll();
    if (result) toastService.success(`Signed out of ${result.sessionsRevoked} session(s)`);
  }

  return (
    <ScreenContainer>
      <Stack gap={7}>
        <AppText variant="headingLarge">Sessions and devices</AppText>

        <Section title="Active sessions">
          {sessions.isLoading ? (
            <LoadingIndicator variant="section" />
          ) : sessions.isError ? (
            <ErrorState title="Couldn't load sessions" onRetry={() => void sessions.refetch()} />
          ) : (
            <Stack gap={3}>
              {sessions.data?.map((session) => (
                <AppCard key={session.session_id} variant="outlined">
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: theme.spacing[3] }}>
                    <Stack gap={1}>
                      <AppText variant="titleMedium">{session.device_name ?? "Unknown device"}</AppText>
                      <AppText variant="caption" color="textTertiary">
                        Last active: {new Date(session.last_active_at).toLocaleString()}
                      </AppText>
                    </Stack>
                    {session.is_current ? (
                      <AppBadge label="This device" tone="info" />
                    ) : (
                      <AppButton
                        label="Sign out"
                        variant="text"
                        size="small"
                        onPress={() => handleRevoke(session)}
                        loading={revokingId === session.session_id}
                        accessibilityLabel={`Sign out ${session.device_name ?? "this device"}`}
                      />
                    )}
                  </View>
                </AppCard>
              ))}
            </Stack>
          )}
        </Section>

        <AppButton label="Sign out of all devices" variant="destructive" size="medium" onPress={() => setConfirmingLogoutAll(true)} loading={loggingOutAll} />
      </Stack>

      <ConfirmationModal
        visible={confirmingLogoutAll}
        title="Sign out of all devices?"
        description="You'll be signed out everywhere, including this device."
        confirmLabel="Sign out everywhere"
        destructive
        onConfirm={handleConfirmLogoutAll}
        onCancel={() => setConfirmingLogoutAll(false)}
      />
    </ScreenContainer>
  );
}
