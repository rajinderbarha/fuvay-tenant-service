import React from "react";
import { View, ScrollView, Pressable } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import { useQuery } from "@tanstack/react-query";
import * as api from "../../services/privacy/privacyApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "PrivacyRequestList">;

const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";

export function PrivacyRequestListScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["privacy-requests"],
    queryFn: async () => {
      const result = await api.listRequests();
      if (!result.ok) throw result.error;
      return result.data.requests;
    },
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Privacy requests" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <PrimaryButton label="New request" onPress={() => navigation.navigate("PrivacyRequestForm", undefined)} fullWidth />
        <View style={{ height: theme.spacing.base }} />
        {query.isLoading ? (
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        ) : query.isError ? (
          <ErrorState icon="cloud-offline-outline" title="Couldn't load requests" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState icon="document-text-outline" title="No requests yet" message="Submit a request to access, correct or erase your data." />
        ) : (
          <Section>
            {query.data.map(req => (
              <Pressable key={req.id} onPress={() => navigation.navigate("PrivacyRequestDetail", { requestId: req.id })} accessibilityRole="button">
                <Card style={{ marginBottom: theme.spacing.sm }}>
                  <AppText variant="caption" color="tertiary">{req.request_number}</AppText>
                  <AppText variant="bodyStrong">{req.request_type.replace(/_/g, " ")}</AppText>
                  <AppText variant="bodySmall" color="warning">{req.status_label}</AppText>
                  <AppText variant="caption" color="tertiary">Submitted {formatDate(req.submitted_at)}</AppText>
                </Card>
              </Pressable>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
