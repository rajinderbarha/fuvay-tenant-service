import React, { useState, useCallback, useMemo } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { StatusBadge } from "../../design-system/components/data-display/Badges";
import { WorkflowStepper } from "../../design-system/components/workflow/WorkflowStepper";
import { NextActionCard } from "../../design-system/components/workflow/NextActionCard";
import { BlockerCard } from "../../design-system/components/workflow/BlockerCard";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert, OfflineBanner } from "../../design-system/components/feedback/Banner";
import { ActionSheet } from "../../design-system/components/overlays/ActionSheet";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { CustomerContactCard } from "./components/CustomerContactCard";
import { useMaskedCall } from "./useMaskedCall";
import { JobDetailsGrid } from "./components/JobDetailsGrid";
import { RequirementsSection } from "./components/RequirementsSection";
import { VisitFeeBanner } from "./components/VisitFeeBanner";
import { useJobDetail } from "./useJobDetail";
import { resolveActionHandling } from "./actionRouting";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { WorkflowStepModel, ActionPresentationModel } from "../../design-system/types";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "JobDetail">;

/**
 * The Job Detail / Execution Command Center (Phase J). Entry point for
 * every job subflow -- never a second execution engine. Every value
 * rendered here comes from GET /v1/staff/service-jobs/{id}/mobile-detail;
 * nothing is derived client-side beyond pure presentation mapping.
 */
export function JobDetailScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";
  const [menuOpen, setMenuOpen] = useState(false);

  const {
    data, isLoading, isError, error, isRefetching, refetch,
    mutating, mutationError, acceptJob, startTravel, markArrived,
  } = useJobDetail(jobId);

  // Masked calling lives beside job detail rather than inside it: calling
  // capability is owned by its own engine and changes independently of the
  // job's execution state (a telephony outage must not invalidate job detail).
  const maskedCall = useMaskedCall(jobId);

  const goBack = useCallback(() => {
    if (navigation.canGoBack()) navigation.goBack();
    else navigation.getParent()?.navigate("AppTabs" as never);
  }, [navigation]);

  const openTimeline = useCallback(() => {
    navigation.navigate("JobTimeline", { jobId, jobReference: data?.job.job_reference });
  }, [navigation, jobId, data]);

  const handleNextAction = useCallback(async () => {
    if (!data) return;
    const handling = resolveActionHandling(data.next_required_action.key);
    if (handling.kind === "mutation") {
      if (handling.mutation === "accept") await acceptJob();
      else if (handling.mutation === "on_the_way") await startTravel();
      else if (handling.mutation === "reached_site") await markArrived();
    } else if (handling.kind === "navigate") {
      navigation.navigate(handling.screen, { jobId, jobReference: data.job.job_reference, targetAction: data.next_required_action.key ?? undefined });
    }
  }, [data, navigation, jobId, acceptJob, startTravel, markArrived]);

  const workflowSteps: WorkflowStepModel[] = useMemo(
    () => (data?.workflow.stages ?? []).map(s => ({ key: s.key, label: s.label, state: s.state })),
    [data],
  );

  const nextAction: ActionPresentationModel | null = useMemo(() => {
    if (!data || !data.next_required_action.key) return null;
    const handling = resolveActionHandling(data.next_required_action.key);
    const enabled = data.next_required_action.allowed && handling.kind !== "blocked" && handling.kind !== "unhandled";
    return {
      code: data.next_required_action.key,
      label: data.next_required_action.label ?? "Continue",
      enabled,
      loading: mutating && handling.kind === "mutation",
      disabledReason: !data.next_required_action.allowed ? data.blocker?.message ?? undefined : undefined,
      tone: "primary",
    };
  }, [data, mutating]);

  const menuOptions = useMemo(() => {
    const options = [{ key: "timeline", label: "View full timeline", icon: "time-outline" as const }];
    if (data && !data.job.is_terminal) options.push({ key: "refresh", label: "Refresh", icon: "refresh-outline" as const } as any);
    return options;
  }, [data]);

  if (isLoading) {
    return (
      <SafeAreaScreen>
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="60%" height={20} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={120} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={80} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    const notFound = error?.backendCode === "ENTITY_NOT_FOUND";
    const notAssigned = error?.code === "ENTITY_NOT_ASSIGNED";
    return (
      <SafeAreaScreen>
        <ErrorState
          icon={notFound || notAssigned ? "lock-closed-outline" : "cloud-offline-outline"}
          title={notFound ? "Job not found" : notAssigned ? "Not assigned to you" : "Couldn't load this job"}
          message={error?.safeMessage ?? "Please try again."}
          actionLabel={notFound || notAssigned ? undefined : "Retry"}
          onAction={notFound || notAssigned ? undefined : () => refetch()}
        />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]} style={{ flex: 0 }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        <AppText variant="bodyStrong" style={{ flex: 1, textAlign: "center" }} numberOfLines={1}>
          Job {data.job.job_reference}
        </AppText>
        <IconButton icon="ellipsis-vertical" accessibilityLabel="More options" onPress={() => setMenuOpen(true)} />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><OfflineBanner /></View> : null}
        {isError && data ? (
          <View style={{ marginBottom: theme.spacing.base }}>
            <InlineAlert tone="warning" title="Some data may be out of date" message={error?.safeMessage ?? "Pull to refresh."} />
          </View>
        ) : null}
        {mutationError ? (
          <View style={{ marginBottom: theme.spacing.base }}>
            <InlineAlert tone="danger" title="Couldn't update this job" message={mutationError.safeMessage} />
          </View>
        ) : null}

        <Section>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, marginBottom: 4 }}>
            <Heading level="large" style={{ flex: 1 }}>{data.job.service_label ?? "Service Job"}</Heading>
            <StatusBadge statusCode={data.job.workflow_status} />
          </View>
          <AppText color="secondary">
            {[data.job.scheduled_date, data.job.scheduled_time_window].filter(Boolean).join(" · ") || "No schedule recorded"}
            {data.job.safe_locality ? ` · ${data.job.safe_locality}` : ""}
          </AppText>
        </Section>

        <Section>
          <CustomerContactCard
            customer={data.customer}
            onCallRelay={() => { void maskedCall.placeCall(); }}
            onMessageRelay={() => {}}
            callAvailable={maskedCall.contact?.can_call}
            cannotCallReason={maskedCall.contact?.cannot_call_reason ?? null}
            calling={maskedCall.calling}
            connectedBefore={maskedCall.contact?.connected_before}
            callError={maskedCall.error?.safeMessage ?? null}
          />
        </Section>

        <Section>
          <WorkflowStepper steps={workflowSteps} />
        </Section>

        {data.blocker ? (
          <Section>
            <BlockerCard blocker={{ code: data.blocker.code, title: "Action needed", message: data.blocker.message ?? "This job is currently blocked.", severity: "warning" }} />
          </Section>
        ) : null}

        {nextAction ? (
          <Section>
            <NextActionCard
              title="Next required action"
              description={!data.next_required_action.allowed ? data.blocker?.message ?? undefined : undefined}
              action={nextAction}
              onPress={handleNextAction}
            />
          </Section>
        ) : data.job.is_terminal ? null : (
          <Section>
            <InlineAlert tone="neutral" title="No action available" message="This job's workflow state isn't recognized yet. Refresh or contact support." />
          </Section>
        )}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.sm }}>Job details</AppText>
          <JobDetailsGrid job={data.job} details={data.job_details} />
        </Section>

        <Section>
          <RequirementsSection requirements={data.requirements} />
        </Section>

        <Section spacing="none">
          <VisitFeeBanner visitFee={data.visit_fee} />
        </Section>
      </ScrollView>

      <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
        <View style={{ flex: 1 }}>
          <SecondaryButton label="View full timeline" onPress={openTimeline} fullWidth />
        </View>
        {nextAction ? (
          <View style={{ flex: 1 }}>
            <PrimaryButton
              label={nextAction.label}
              onPress={handleNextAction}
              disabled={!nextAction.enabled}
              loading={nextAction.loading}
              fullWidth
            />
          </View>
        ) : null}
      </View>

      <ActionSheet
        visible={menuOpen}
        title="Job options"
        options={menuOptions}
        onSelect={key => { if (key === "timeline") openTimeline(); else if (key === "refresh") refetch(); }}
        onClose={() => setMenuOpen(false)}
      />
    </SafeAreaScreen>
  );
}
