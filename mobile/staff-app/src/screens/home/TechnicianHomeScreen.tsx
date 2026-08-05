import React, { useState, useCallback, useMemo } from "react";
import { View, Pressable, RefreshControl } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTheme } from "../../design-system/themes";
import { ScrollScreen } from "../../design-system/components/foundation/ScrollScreen";
import { Card, Section, Stack, Inline, Divider } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { Caption } from "../../design-system/components/typography/Label";
import { Icon } from "../../design-system/components/Icon";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert, OfflineBanner } from "../../design-system/components/feedback/Banner";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { EmptyState, PartialDataNotice } from "../../design-system/components/feedback/States";
import { StatusBadge } from "../../design-system/components/data-display/Badges";
import { MetricCard } from "../../design-system/components/data-display/MetricCard";
import { CustomerAlias } from "../../design-system/components/data-display/Privacy";
import { AvailabilitySelector } from "./components/AvailabilitySelector";
import { useTechnicianHome } from "./useTechnicianHome";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { AvailabilityState, CurrentJobDTO, ScheduleRowDTO, ActionRequiredItemDTO } from "../../services/home/types";

const EXECUTION_ROUTE_FOR_ACTION: Record<string, string> = {
  start_inspection: "Inspection",
  complete: "CompletionProof",
};

function todayLabel(): string {
  return new Intl.DateTimeFormat("en-US", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function TechnicianHomeScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<any>();
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const { data, isLoading, isError, error, isRefetching, refetch, updateAvailability, lastUpdatedAt } = useTechnicianHome();
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);

  const openJob = useCallback((jobId: string, jobReference: string, targetAction?: string) => {
    const screen = (targetAction && EXECUTION_ROUTE_FOR_ACTION[targetAction]) || "JobDetail";
    navigation.getParent()?.navigate("JobExecutionStack", { screen, params: { jobId, jobReference, targetAction } });
  }, [navigation]);

  const handleAvailabilityChange = useCallback(async (next: AvailabilityState) => {
    setAvailabilityError(null);
    const result = await updateAvailability(next);
    if (result && !result.ok) {
      setAvailabilityError(result.error.safeMessage);
    }
  }, [updateAvailability]);

  const lastUpdatedLabel = useMemo(() => {
    if (!lastUpdatedAt) return undefined;
    return new Date(lastUpdatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }, [lastUpdatedAt]);

  if (isLoading) {
    return (
      <ScrollScreen contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Skeleton width="60%" height={28} />
        <View style={{ marginTop: 8, marginBottom: theme.spacing.lg }}>
          <Skeleton width="40%" height={16} />
        </View>
        <Skeleton width="100%" height={220} radius={theme.radiusUsage.card} />
        <View style={{ marginTop: theme.spacing.base }}>
          <Skeleton width="100%" height={72} radius={theme.radiusUsage.card} />
        </View>
        <View style={{ marginTop: theme.spacing.base }}>
          <Skeleton width="100%" height={140} radius={theme.radiusUsage.card} />
        </View>
      </ScrollScreen>
    );
  }

  if (isError && !data) {
    const offlineWithNoCache = offline;
    return (
      <ScrollScreen contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: theme.spacing.lg }}>
        <EmptyState
          icon={offlineWithNoCache ? "cloud-offline-outline" : "alert-circle-outline"}
          title={offlineWithNoCache ? "You're offline" : "Couldn't load your Home screen"}
          message={offlineWithNoCache ? "Connect to the internet to load your work." : (error?.safeMessage ?? "Please try again.")}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      </ScrollScreen>
    );
  }

  if (!data) return null;

  return (
    <ScrollScreen
      contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
    >
      {offline ? <OfflineBanner lastSyncedLabel={lastUpdatedLabel} /> : null}

      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.base }}>
        <View>
          <Heading level="large">{greeting()}, {data.technician.display_name}</Heading>
          <AppText color="secondary">{todayLabel()}</AppText>
        </View>
        <Inline gap="sm">
          <IconButton
            icon="notifications-outline"
            accessibilityLabel={data.unread_notification_count > 0 ? `Notifications, ${data.unread_notification_count} unread` : "Notifications"}
            onPress={() => navigation.navigate("Notifications")}
          />
        </Inline>
      </View>

      <View style={{ alignItems: "flex-end", marginBottom: theme.spacing.base }}>
        <AvailabilitySelector
          state={data.availability.state}
          disabled={offline}
          onChange={handleAvailabilityChange}
        />
      </View>
      {availabilityError ? <InlineAlert tone="danger" title="Couldn't update availability" message={availabilityError} /> : null}

      <Section spacing="lg">
        {data.current_job ? (
          <CurrentJobSection job={data.current_job} offline={offline} onPress={openJob} />
        ) : (
          <Card>
            <EmptyState
              icon="checkmark-done-outline"
              title="No active job right now"
              message="You have no active job right now."
              actionLabel="View today's jobs"
              onAction={() => navigation.navigate("Jobs")}
            />
          </Card>
        )}
      </Section>

      <Section spacing="lg">
        <Inline gap="sm">
          <MetricCard label="Jobs today" value={String(data.shift_summary.jobs_today)} icon="briefcase-outline" />
          <MetricCard label="Completed" value={String(data.shift_summary.completed)} icon="checkmark-circle-outline" tone="success" />
          <MetricCard label="Remaining" value={String(data.shift_summary.remaining)} icon="time-outline" />
        </Inline>
      </Section>

      <Section spacing="lg">
        <AppText variant="title" style={{ marginBottom: theme.spacing.sm }}>Today's schedule</AppText>
        {data.today_schedule.length === 0 ? (
          <Card><AppText color="secondary">No jobs scheduled today.</AppText></Card>
        ) : (
          <Card padding="none">
            {data.today_schedule.map((row, index) => (
              <View key={row.job_id}>
                {index > 0 ? <Divider /> : null}
                <ScheduleRow row={row} onPress={() => openJob(row.job_id, row.job_reference)} />
              </View>
            ))}
          </Card>
        )}
      </Section>

      <Section spacing="lg">
        <AppText variant="title" style={{ marginBottom: theme.spacing.sm }}>Action required</AppText>
        {data.action_required.length === 0 ? (
          <Card><AppText color="secondary">Nothing needs your attention right now.</AppText></Card>
        ) : (
          <Card padding="none">
            {data.action_required.map((item, index) => (
              <View key={`${item.job_id}-${item.key}`}>
                {index > 0 ? <Divider /> : null}
                <ActionRequiredRow item={item} onPress={() => openJob(item.job_id, item.job_reference)} />
              </View>
            ))}
          </Card>
        )}
      </Section>

      {isError && data ? (
        <PartialDataNotice message="Some data may be out of date." onRetry={() => refetch()} />
      ) : null}
    </ScrollScreen>
  );
}

function CurrentJobSection({ job, offline, onPress }: { job: CurrentJobDTO; offline: boolean; onPress: (jobId: string, jobReference: string, targetAction?: string) => void }) {
  const { theme } = useTheme();
  const actionDisabled = offline || !job.next_required_action.allowed;
  return (
    <Card>
      <AppText variant="label" color="tertiary" style={{ marginBottom: 4 }}>Current job</AppText>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.xs }}>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">{job.job_reference} · {job.service_label ?? "Service"}</AppText>
        </View>
        <StatusBadge statusCode={job.workflow_status} />
      </View>
      <Inline gap="sm" style={{ marginBottom: 4 }}>
        <Icon name="calendar-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="bodySmall" color="secondary">{job.scheduled_time_window ?? "Unscheduled"}</AppText>
      </Inline>
      {job.locality_label ? (
        <Inline gap="sm" style={{ marginBottom: 4 }}>
          <Icon name="location-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="bodySmall" color="secondary">{job.locality_label}</AppText>
        </Inline>
      ) : null}
      <View style={{ marginBottom: theme.spacing.sm }}>
        <CustomerAlias alias={job.customer_alias} />
      </View>

      {job.blocker ? (
        <InlineAlert tone="warning" title="Action blocked" message={job.blocker.message ?? job.blocker.code} />
      ) : null}

      {job.next_required_action.label ? (
        <PrimaryButton
          label={job.next_required_action.label}
          onPress={() => onPress(job.job_id, job.job_reference, job.next_required_action.key ?? undefined)}
          disabled={actionDisabled}
          fullWidth
          accessibilityLabel={`Job ${job.job_reference}, ${job.service_label ?? "Service"}, ${job.workflow_status}. ${job.next_required_action.label}.`}
        />
      ) : null}
      <View style={{ marginTop: theme.spacing.xs }}>
        <SecondaryButton label="View details" onPress={() => onPress(job.job_id, job.job_reference)} fullWidth />
      </View>
    </Card>
  );
}

function ScheduleRow({ row, onPress }: { row: ScheduleRowDTO; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`Job ${row.job_reference}, ${row.workflow_status}, scheduled ${row.scheduled_time_window ?? "time not set"}`}
      style={{ flexDirection: "row", alignItems: "center", padding: theme.spacing.md, gap: theme.spacing.sm, minHeight: 44 }}
    >
      <AppText variant="bodySmall" color="tertiary" style={{ width: 64 }}>{row.scheduled_time_window ?? "--"}</AppText>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{row.job_reference}</AppText>
        {row.locality_label ? <Caption color="tertiary">{row.locality_label}</Caption> : null}
      </View>
      <StatusBadge statusCode={row.workflow_status} />
      <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
    </Pressable>
  );
}

function ActionRequiredRow({ item, onPress }: { item: ActionRequiredItemDTO; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${item.label}, job ${item.job_reference}`}
      style={{ flexDirection: "row", alignItems: "center", padding: theme.spacing.md, gap: theme.spacing.sm, minHeight: 44 }}
    >
      <Icon name="alert-circle-outline" size="standard" color={theme.colors.statusWarning} decorative />
      <AppText style={{ flex: 1 }}>{item.label}</AppText>
      <Icon name="chevron-forward" size="compact" color={theme.colors.textTertiary} decorative />
    </Pressable>
  );
}
