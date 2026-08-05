import React, { useCallback, useState } from "react";
import { View, ScrollView, RefreshControl } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { TextArea } from "../../design-system/components/forms/TextArea";
import { Skeleton } from "../../design-system/components/feedback/Loading";
import { ErrorState } from "../../design-system/components/feedback/States";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { PrimaryButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { ChecklistItemRow } from "../inspection/components/ChecklistItemRow";
import { WorkFinishedBanner } from "./components/WorkFinishedBanner";
import { EvidenceGrid } from "./components/EvidenceGrid";
import { PartsUsedList } from "./components/PartsUsedList";
import { CustomerHandoverCard } from "./components/CustomerHandoverCard";
import { useCompletionProof } from "./useCompletionProof";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { JobExecutionStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<JobExecutionStackParamList, "CompletionProof">;

/**
 * Completion Proof & Customer Handover (Phase N). Submitting proof never
 * confirms payment or triggers final completion/commission -- those remain
 * separate, later, canonical actions (spec sections 15, 16).
 */
export function CompletionProofScreen({ route, navigation }: Props) {
  const { theme } = useTheme();
  const { jobId } = route.params;
  const networkStatus = useNetworkStatus();
  const offline = networkStatus.networkState === "offline";

  const [resolutionSummary, setResolutionSummary] = useState<string | null>(null);
  const [serviceNotes, setServiceNotes] = useState<string | null>(null);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);

  const {
    data, isLoading, isError, error, isRefetching, refetch,
    mutating, mutationError, uploadingCategory,
    saveDraft, addEvidenceFromUpload, removeEvidence, submit, requestHandover, sendReminder, markCustomerUnavailable,
  } = useCompletionProof(jobId);

  const goBack = useCallback(() => navigation.navigate("JobDetail", { jobId }), [navigation, jobId]);

  const summaryValue = resolutionSummary ?? data?.proof.resolution_summary ?? "";
  const notesValue = serviceNotes ?? data?.proof.final_service_notes ?? "";

  const handleBlurSave = useCallback(() => {
    saveDraft({ resolution_summary: summaryValue, final_service_notes: notesValue });
  }, [saveDraft, summaryValue, notesValue]);

  const handleSubmit = useCallback(async () => {
    const result = await submit();
    if (result.ok) { /* stay on screen to show submitted read-only state + handover controls */ }
  }, [submit]);

  const handleAddEvidence = useCallback(async (category: "before" | "after") => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) return;
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    await addEvidenceFromUpload(category, asset.uri, asset.fileName ?? "evidence.jpg", asset.mimeType ?? "image/jpeg");
  }, [addEvidenceFromUpload]);

  if (isLoading) {
    return (
      <SafeAreaScreen>
        <View style={{ padding: theme.spacing.lg }}>
          <Skeleton width="60%" height={20} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={120} radius={theme.radiusUsage.card} />
          <View style={{ height: theme.spacing.sm }} />
          <Skeleton width="100%" height={200} radius={theme.radiusUsage.card} />
        </View>
      </SafeAreaScreen>
    );
  }

  if (isError && !data) {
    return (
      <SafeAreaScreen>
        <ErrorState icon="cloud-offline-outline" title="Couldn't load completion proof" message={error?.safeMessage ?? "Please try again."} actionLabel="Retry" onAction={() => refetch()} />
      </SafeAreaScreen>
    );
  }

  if (!data) return null;

  if (data.job.workflow_status !== "work_done" && data.proof.status !== "submitted") {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
          <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        </View>
        <ErrorState icon="lock-closed-outline" title="Work isn't finished yet" message="Completion proof opens once Work Execution has reached Finish Work." />
      </SafeAreaScreen>
    );
  }

  const isDraft = data.proof.status === "draft";
  const isEditable = isDraft && !offline;
  const canSubmit = data.allowed_actions.includes("submit_proof");

  return (
    <SafeAreaScreen edges={["top", "left", "right"]} style={{ flex: 0 }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={goBack} />
        <View style={{ flex: 1, alignItems: "center" }}>
          <AppText variant="bodyStrong">Completion proof</AppText>
          <AppText variant="caption" color="tertiary">{data.job.job_reference}</AppText>
        </View>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl }}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.brandPrimary} />}
      >
        {offline ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="neutral" title="Offline" message="Completion proof is read-only until you reconnect." /></View> : null}
        {mutationError ? <View style={{ marginBottom: theme.spacing.base }}><InlineAlert tone="danger" title="Couldn't complete that action" message={mutationError.safeMessage} /></View> : null}

        <Section>
          <WorkFinishedBanner
            workSummary={data.work_summary}
            checklistLabel={`All work checklist items completed${data.work_summary.approved_quote_version ? ` · Estimate v${data.work_summary.approved_quote_version}` : ""}`}
          />
        </Section>

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Resolution summary</AppText>
          <Card>
            <TextArea
              value={summaryValue}
              onChangeText={setResolutionSummary}
              onBlur={handleBlurSave}
              editable={isEditable}
              placeholder="Describe the diagnosed issue, work performed and final test result…"
              minLines={3}
            />
          </Card>
        </Section>

        {data.definition.final_checks.length > 0 ? (
          <Section>
            <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Final checks</AppText>
            <Card padding="base">
              {data.definition.final_checks.map(item => (
                <ChecklistItemRow
                  key={item.id}
                  item={item}
                  disabled={!isEditable}
                  saving={savingItemId === item.id}
                  uploading={false}
                  onSave={() => {}}
                  onPickEvidence={async () => ({ ok: false })}
                />
              ))}
            </Card>
          </Section>
        ) : null}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Before & after evidence</AppText>
          <Card padding="base">
            <EvidenceGrid
              beforeIds={data.proof.before_photo_ids}
              afterIds={data.proof.after_photo_ids}
              editable={isEditable}
              uploadingCategory={uploadingCategory}
              onAddBefore={() => handleAddEvidence("before")}
              onAddAfter={() => handleAddEvidence("after")}
              onRemove={(category, fileId) => removeEvidence(category, fileId)}
            />
            {data.readiness.missing_evidence_categories.includes("after") ? (
              <AppText variant="caption" color="warning" style={{ marginTop: theme.spacing.xs }}>Minimum 1 after photo required</AppText>
            ) : null}
          </Card>
        </Section>

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Parts used</AppText>
          <Card padding="base">
            <PartsUsedList parts={data.parts_used} />
          </Card>
        </Section>

        {data.proof.status === "submitted" ? (
          <Section>
            <CustomerHandoverCard
              status={data.proof.handover_status}
              onRequest={requestHandover}
              onSendReminder={sendReminder}
              onMarkUnavailable={markCustomerUnavailable}
              canRequest={data.allowed_actions.includes("request_handover")}
              canRemind={data.allowed_actions.includes("send_reminder")}
              disabled={mutating || offline}
            />
          </Section>
        ) : null}

        <Section>
          <AppText variant="title" style={{ marginBottom: theme.spacing.xs }}>Final service notes</AppText>
          <Card>
            <TextArea
              value={notesValue}
              onChangeText={setServiceNotes}
              onBlur={handleBlurSave}
              editable={isEditable}
              placeholder="Care instructions or warranty notes…"
              minLines={2}
            />
          </Card>
        </Section>

        <InlineAlert tone="info" message="Submitting proof does not confirm payment or complete the job." />
      </ScrollView>

      {isDraft && !offline ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Save draft" onPress={handleBlurSave} fullWidth />
          </View>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Submit completion proof" onPress={handleSubmit} disabled={!canSubmit} loading={mutating} fullWidth />
          </View>
        </View>
      ) : null}
    </SafeAreaScreen>
  );
}
