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

const OUTCOME_ICON: Record<string, { name: "checkmark-circle" | "alert-circle" | "help-circle"; color: (theme: ReturnType<typeof useTheme>["theme"]) => string }> = {
  successful: { name: "checkmark-circle", color: t => t.colors.statusSuccess },
  verification_required: { name: "alert-circle", color: t => t.colors.statusWarning },
  blocked: { name: "alert-circle", color: t => t.colors.statusDanger },
  unknown: { name: "help-circle", color: t => t.colors.textTertiary },
};

/** Security Activity (Phase V spec section 12). Read-only, safe-projected
 * feed over the real LoginEvent table via GET /v1/auth/me/login-activity
 * (cursor-paginated) -- label/outcome/channel/device_name are all backend-
 * computed and pre-masked, never raw. */
export function SecurityActivityScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["security-activity"],
    queryFn: async () => {
      const result = await securityApi.getSecurityActivity("all", 50);
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
        ) : !query.data || query.data.events.length === 0 ? (
          <EmptyState icon="shield-outline" title="No activity yet" message="Security events will appear here." />
        ) : (
          <Section>
            {query.data.events.map(item => {
              const icon = OUTCOME_ICON[item.outcome] ?? OUTCOME_ICON.unknown;
              return (
                <Card key={item.event_id} style={{ marginBottom: theme.spacing.sm }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <View style={{ flex: 1 }}>
                      <AppText variant="bodyStrong">{item.label}</AppText>
                      <AppText variant="caption" color="tertiary">{new Date(item.occurred_at).toLocaleString()}</AppText>
                      <AppText variant="caption" color="tertiary">
                        {item.channel} · {item.device_name}{item.is_current_device ? " (this device)" : ""}
                      </AppText>
                    </View>
                    <Icon name={icon.name} size="compact" color={icon.color(theme)} decorative />
                  </View>
                </Card>
              );
            })}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
