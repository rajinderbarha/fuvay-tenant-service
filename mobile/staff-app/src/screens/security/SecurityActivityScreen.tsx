import React from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Icon } from "../../design-system/components/Icon";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import * as securityApi from "../../services/auth/securityApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "SecurityActivity">;

const ACTIVITY_LABEL: Record<string, string> = {
  "auth.login_success": "Successful sign-in",
  "auth.login_failed": "Failed sign-in attempt",
  "auth.password_changed": "Password changed",
  "mfa.enabled": "Two-step verification enabled",
  "mfa.disabled": "Two-step verification disabled",
  "mfa.backup_codes_regenerated": "Recovery codes regenerated",
  "device.trust_removed": "Trusted device removed",
  "device.trust_added": "Trusted device added",
  "session.revoked": "Session revoked",
};

/** Security Activity (Phase V spec section 12). Read-only, safe-projected
 * feed over the real AuthAuditLog (self-scoped, never platform admin data)
 * -- IP is pre-masked server-side, never raw. */
export function SecurityActivityScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["security-activity"],
    queryFn: async () => {
      const result = await securityApi.getSecurityActivity(50, 0);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Security activity" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {query.isLoading ? (
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        ) : query.isError ? (
          <ErrorState icon="cloud-offline-outline" title="Couldn't load activity" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
        ) : !query.data || query.data.items.length === 0 ? (
          <EmptyState icon="shield-outline" title="No activity yet" message="Security events will appear here." />
        ) : (
          <Section>
            {query.data.items.map(item => (
              <Card key={item.id} style={{ marginBottom: theme.spacing.sm }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <View style={{ flex: 1 }}>
                    <AppText variant="bodyStrong">{ACTIVITY_LABEL[item.action_type] ?? item.action_type}</AppText>
                    <AppText variant="caption" color="tertiary">{new Date(item.created_at).toLocaleString()}</AppText>
                    {item.ip_masked ? <AppText variant="caption" color="tertiary">From {item.ip_masked}</AppText> : null}
                    {item.failure_reason ? <AppText variant="bodySmall" color="danger">{item.failure_reason}</AppText> : null}
                  </View>
                  <Icon
                    name={item.outcome === "success" ? "checkmark-circle" : "alert-circle"}
                    size="compact"
                    color={item.outcome === "success" ? theme.colors.statusSuccess : theme.colors.statusDanger}
                    decorative
                  />
                </View>
              </Card>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
