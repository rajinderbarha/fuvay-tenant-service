import React from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import * as api from "../../services/privacy/privacyApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "ConsentHistory">;

const ACTION_LABEL: Record<string, string> = { granted: "Enabled", withdrawn: "Disabled", expired: "Expired", updated: "Updated" };
const TYPE_LABEL: Record<string, string> = { analytics: "Product improvement", marketing: "Optional updates" };

/** Consent History (Phase X spec section 4). Read-only, append-only ledger
 * -- every past choice is preserved, never overwritten (spec section 6:
 * "Do not delete prior records when consent is withdrawn"). */
export function ConsentHistoryScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["consent-history"],
    queryFn: async () => {
      const result = await api.getConsentHistory();
      if (!result.ok) throw result.error;
      return result.data.items;
    },
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Consent history" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {query.isLoading ? (
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        ) : query.isError ? (
          <ErrorState icon="cloud-offline-outline" title="Couldn't load history" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState icon="time-outline" title="No changes yet" message="Your consent choices haven't changed." />
        ) : (
          <Section>
            {query.data.map(item => (
              <Card key={item.id} style={{ marginBottom: theme.spacing.sm }}>
                <AppText variant="bodyStrong">{TYPE_LABEL[item.consent_type] ?? item.consent_type}</AppText>
                <AppText variant="bodySmall" color={item.action === "granted" ? "success" : "tertiary"}>{ACTION_LABEL[item.action] ?? item.action}</AppText>
                <AppText variant="caption" color="tertiary">{new Date(item.created_at).toLocaleString()} · Policy {item.policy_version}</AppText>
              </Card>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
