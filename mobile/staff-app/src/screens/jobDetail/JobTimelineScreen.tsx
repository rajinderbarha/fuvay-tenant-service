import React from "react";
import { View, ScrollView } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { MobileHeader } from "../../design-system/components/navigation/MobileHeader";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, ErrorState } from "../../design-system/components/feedback/States";
import { ActivityRow } from "../../design-system/components/data-display/Timeline";
import * as jobDetailApi from "../../services/jobDetail/jobDetailApi";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "JobTimeline">;

/**
 * Read-only, canonical timeline (spec section 15). Renders exactly the
 * events the backend returns -- no fabricated/inferred history entries.
 */
export function JobTimelineScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId, jobReference } = route.params;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["jobs", "timeline", jobId],
    queryFn: async ({ signal }) => {
      const result = await jobDetailApi.getJobTimeline(jobId, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });
  const safeError = error as { safeMessage?: string } | null;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <MobileHeader title={`Timeline · ${jobReference ?? jobId}`} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        {isLoading ? (
          <View>
            <Skeleton width="100%" height={40} />
            <View style={{ height: theme.spacing.sm }} />
            <Skeleton width="100%" height={40} />
          </View>
        ) : isError ? (
          <ErrorState title="Couldn't load timeline" message={safeError?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
        ) : !data || data.entries.length === 0 ? (
          <EmptyState icon="time-outline" title="No activity yet" message="Timeline events will appear here as the job progresses." />
        ) : (
          data.entries.map((entry, i) => (
            <ActivityRow key={`${entry.event_type}-${i}`} actorLabel={entry.event_type.replace(/_/g, " ")} description={entry.notes ?? entry.label} isoTimestamp={entry.created_at} />
          ))
        )}
      </ScrollView>
    </SafeAreaScreen>
  );
}
