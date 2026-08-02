import React, { useCallback, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section, Inline } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { PrimaryButton, SecondaryButton, TertiaryButton } from "../../design-system/components/actions/Buttons";
import { ApprovedScopeBanner } from "./components/ApprovedScopeBanner";
import { WorkSessionCard } from "./components/WorkSessionCard";
import { PartsSection } from "./components/PartsSection";
import { RequestPartSheet } from "./components/RequestPartSheet";
import { ChecklistItemRow } from "../inspection/components/ChecklistItemRow";
import { uploadChecklistEvidence } from "../../services/media/mediaApi";
import { useWorkExecution } from "./useWorkExecution";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "Checklist">;

/**
 * Work Execution command center (Phase M). "Finish Work" moves the job to
 * work_done only -- never final Completed (spec sections 16, 17); that
 * later transition/commission trigger is out of scope here.
 */
export function WorkExecutionScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus === "offline" || networkStatus === "internet_reachable_false";
  const [requestPartOpen, setRequestPartOpen] = useState(false);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [uploadingItemId, setUploadingItemId] = useState<string | null>(null);

  const {
    data, isLoading, isError, error, isRefetching, refetch,
    mutating, mutationError, startWork, pauseWork, resumeWork, finishWork, requestPart, saveChecklistResponse,
  } = useWorkExecution(jobId);

  const goBack = useCallback(() => navigation.navigate("JobDetail", { jobId }), [navigation, jobId]);
  const viewEstimate = useCallback(() => navigation.navigate("Estimate", { jobId }), [navigation, jobId]);

  const handleStart = useCallback(async () => { await startWork(); }, [startWork]);
  const handleFinish = useCallback(async () => {
    const result = await finishWork();
    if (result.ok) goBack();
  }, [finishWork, goBack]);

  const handleSaveItem = useCallback(async (itemId: string, value: any, evidence: any) => {
    if (!data?.checklist.instance_id) return;
    setSavingItemId(itemId);
    await saveChecklistResponse(data.checklist.instance_id, itemId, value, evidence);
    setSavingItemId(null);
  }, [data, saveChecklistResponse]);

  const handlePickEvidence = useCallback(async (itemId: string): Promise<{ ok: boolean; fileId?: string }> => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) return { ok: false };
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (result.canceled || !result.assets?.[0]) return { ok: false };
    const asset = result.assets[0];
    setUploadingItemId(itemId);
    const upload = await uploadChecklistEvidence(jobId, asset.uri, asset.fileName ?? "evidence.jpg", asset.mimeType ?? "image/jpeg");
    setUploadingItemId(null);
    if (!upload.ok) return { ok: false };
    return { ok: true, fileId: upload.data.id };
  }, [jobId]);

  if (isLoading) {
    return (
      <SafeAreaScreen>
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="60%" height={20} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={100} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={160} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load work execution" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  const canStart = data.allowed_actions.includes("start_work");
  const canPause = data.allowed_actions.includes("pause_work");
  const canResume = data.allowed_actions.includes("resume_work");
  const canFinish = data.allowed_actions.includes("finish_work");
  const remaining = data.checklist.required_total - data.checklist.required_completed;
  const isReadOnly = data.job.is_terminal || data.job.workflow_status === "work_done" || offline;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]} style={{ flex: 0 }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        <View style={{ flex: 1, alignItems: "center" }}>
          <AppText variant="bodyStrong">Work in progress</AppText>
          <AppText variant="caption" color="tertiary">{data.job.job_reference}</AppText>
        </View>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Work execution is read-only until you reconnect." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        {data.approved_scope ? (
          <Section>
            <ApprovedScopeBanner scope={data.approved_scope} onView={viewEstimate} />
          </Section>
        ) : (
          <Section>
            <InlineAlert tone="warning" title="No approved estimate" message="Work cannot start until the customer approves the current estimate." />
          </Section>
        )}

        {canStart ? (
          <Section>
            <Card style={{ alignItems: "center" }}>
              <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>Ready to start work</AppText>
              <PrimaryButton label="Start work" onPress={handleStart} loading={mutating} disabled={offline} fullWidth />
            </Card>
          </Section>
        ) : data.work_session ? (
          <Section>
            <WorkSessionCard session={data.work_session} onPause={() => pauseWork()} onResume={resumeWork} disabled={mutating || offline || !(canPause || canResume)} />
          </Section>
        ) : null}

        {data.checklist.items.length > 0 ? (
          <Section>
            <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Work checklist</AppText>
            <Card padding="base">
              {data.checklist.items.map(item => (
                <ChecklistItemRow
                  key={item.id}
                  item={item}
                  disabled={isReadOnly || !data.work_session || data.work_session.state !== "active"}
                  saving={savingItemId === item.id}
                  uploading={uploadingItemId === item.id}
                  onSave={(value, evidence) => handleSaveItem(item.id, value, evidence)}
                  onPickEvidence={() => handlePickEvidence(item.id)}
                />
              ))}
            </Card>
          </Section>
        ) : null}

        <Section>
          <Inline justify="space-between" style={{ marginBottom: theme.spacing.xs }}>
            <AppText variant="title">Parts & materials</AppText>
            {data.parts.length > 0 ? (
              <AppText variant="bodySmall" color="link" onPress={() => navigation.navigate("PartsRequest", { jobId })}>
                View all
              </AppText>
            ) : null}
          </Inline>
          <Card padding="base">
            <PartsSection parts={data.parts} />
            {!isReadOnly ? (
              <TertiaryButton label="+ Request part" onPress={() => setRequestPartOpen(true)} fullWidth />
            ) : null}
          </Card>
        </Section>

        {data.readiness.blockers.length > 0 && !canStart ? (
          <InlineAlert
            tone="warning"
            message={
              remaining > 0
                ? `${remaining} checklist item${remaining > 1 ? "s" : ""}${data.readiness.pending_part_request_ids.length > 0 ? ` and ${data.readiness.pending_part_request_ids.length} part approval remaining` : " remaining"}`
                : data.readiness.pending_part_request_ids.length > 0
                  ? `${data.readiness.pending_part_request_ids.length} part approval remaining`
                  : "Some requirements are still outstanding."
            }
          />
        ) : null}
      </ScrollView>

      {!canStart && data.work_session && !isReadOnly ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Save progress" onPress={() => { void refetch(); }} fullWidth />
          </View>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Finish work" onPress={handleFinish} disabled={!canFinish} loading={mutating} fullWidth />
          </View>
        </View>
      ) : null}

      <RequestPartSheet
        visible={requestPartOpen}
        onClose={() => setRequestPartOpen(false)}
        submitting={mutating}
        onSubmit={async body => {
          const result = await requestPart(body);
          if (result.ok) setRequestPartOpen(false);
        }}
      />
    </SafeAreaScreen>
  );
}
