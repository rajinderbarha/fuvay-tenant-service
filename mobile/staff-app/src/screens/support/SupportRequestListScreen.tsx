import React from "react";
import { View, ScrollView, Pressable } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import * as api from "../../services/support/supportApi";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "SupportRequestList">;

export function SupportRequestListScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const query = useQuery({
    queryKey: ["support-requests"],
    queryFn: async () => {
      const result = await api.listRequests();
      if (!result.ok) throw result.error;
      return result.data.requests;
    },
  });

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Your requests" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <PrimaryButton label="Create support request" onPress={() => navigation.navigate("CreateSupportRequest", undefined)} fullWidth />
        <View style={{ height: theme.spacing.base }} />
        {query.isLoading ? (
          <Skeleton width="100%" height={300} radius={theme.radiusUsage.card} />
        ) : query.isError ? (
          <ErrorState icon="cloud-offline-outline" title="Couldn't load requests" message="Please try again." actionLabel="Retry" onAction={() => query.refetch()} />
        ) : !query.data || query.data.length === 0 ? (
          <EmptyState icon="chatbox-ellipses-outline" title="No requests yet" message="Create a request if you need help." />
        ) : (
          <Section>
            {query.data.map(req => (
              <Pressable key={req.id} onPress={() => navigation.navigate("SupportRequestDetail", { requestId: req.id })} accessibilityRole="button">
                <Card style={{ marginBottom: theme.spacing.sm }}>
                  <AppText variant="caption" color="tertiary">{req.ticket_number}</AppText>
                  <AppText variant="bodyStrong">{req.subject}</AppText>
                  <AppText variant="bodySmall" color="info">{req.status_label}</AppText>
                  <AppText variant="caption" color="tertiary">{req.category_label}</AppText>
                </Card>
              </Pressable>
            ))}
          </Section>
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
