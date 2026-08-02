import React from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState } from "../../design-system/components/feedback/States";
import { useDocumentHistory } from "./useDocumentHistory";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "DocumentHistory">;

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";

const STATUS_LABEL: Record<string, string> = {
  verified: "Verified", pending_review: "Under review", rejected: "Rejected",
  changes_requested: "Changes requested", superseded: "Superseded",
};

/** Safe version history (spec section 6, 9) -- shows every prior version's
 * decision without exposing raw file paths or storage identifiers. */
export function DocumentHistoryScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { docCode } = route.params;
  const { versions, isLoading } = useDocumentHistory(docCode);

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Version history" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {isLoading ? (
          <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
        ) : versions.length === 0 ? (
          <EmptyState icon="time-outline" title="No history yet" message="This document hasn't been submitted." />
        ) : (
          <Section>
            {versions.map(v => (
              <Card key={v.id} style={{ marginBottom: theme.spacing.sm, opacity: v.is_current ? 1 : 0.75 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <AppText variant="bodyStrong">Version {v.version}{v.is_current ? " (current)" : ""}</AppText>
                  <AppText variant="labelStrong" color={v.status === "verified" ? "success" : v.status === "rejected" ? "danger" : "tertiary"}>
                    {STATUS_LABEL[v.status] ?? v.status}
                  </AppText>
                </View>
                <AppText variant="caption" color="tertiary">Submitted {formatDate(v.submitted_at)}</AppText>
                {v.verified_at ? <AppText variant="caption" color="tertiary">Verified {formatDate(v.verified_at)}</AppText> : null}
                {v.rejection_reason ? <AppText variant="bodySmall" color="danger">{v.rejection_reason}</AppText> : null}
                {v.review_notes ? <AppText variant="bodySmall" color="tertiary">{v.review_notes}</AppText> : null}
              </Card>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
