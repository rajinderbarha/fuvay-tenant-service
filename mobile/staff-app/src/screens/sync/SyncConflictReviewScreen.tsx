import React, { useEffect, useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { SecondaryButton, DestructiveButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { useSession } from "../../navigation/session/SessionProvider";
import { loadQueue, saveQueue } from "../../services/sync/queueStorage";
import { buildQueueItem } from "../../services/sync/syncEngine";
import { QueueItem } from "../../services/sync/types";

type Props = NativeStackScreenProps<ProfileStackParamList, "SyncConflictReview">;

const CONFLICT_COPY: Record<string, { title: string; message: string }> = {
  ESTIMATE_CREATE: { title: "Estimate draft conflict", message: "A newer estimate version exists on the server." },
  ESTIMATE_REVISE: { title: "Estimate draft conflict", message: "A newer estimate version exists on the server." },
  DEFAULT: { title: "Sync conflict", message: "This item can no longer be safely applied as-is -- a newer version exists on the server." },
};

/**
 * Conflict review (Phase Z spec section 12). Never offers "force upload"
 * for a workflow state -- only the three safe resolutions the spec lists:
 * keep the local notes as a new draft, discard, or go look at the current
 * server state. Automatic retry has already stopped for this item (it
 * reached `conflict` in syncEngine and syncEngine never retries that
 * state).
 */
export function SyncConflictReviewScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { accessContext } = useSession();
  const [item, setItem] = useState<QueueItem | null>(null);

  useEffect(() => {
    if (!accessContext.userId || !accessContext.tenantId) return;
    loadQueue(accessContext.userId, accessContext.tenantId).then(items => {
      setItem(items.find(i => i.local_id === route.params.localId) ?? null);
    });
  }, [accessContext.userId, accessContext.tenantId, route.params.localId]);

  if (!item) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Sync conflict" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}><AppText color="secondary">This item is no longer in the queue.</AppText></View>
      </SafeAreaScreen>
    );
  }

  const copy = CONFLICT_COPY[item.operation_type] ?? CONFLICT_COPY.DEFAULT;

  const saveAsNewDraft = async () => {
    if (!accessContext.userId || !accessContext.tenantId) return;
    const items = await loadQueue(accessContext.userId, accessContext.tenantId);
    const draft = buildQueueItem({
      operation_type: item.operation_type, tenant_id: item.tenant_id, vertical_code: item.vertical_code,
      job_id: item.job_id, entity_id: item.entity_id, title: `${item.title} (my notes)`, job_reference: item.job_reference,
      payload: item.payload,
    });
    await saveQueue(accessContext.userId, accessContext.tenantId, [
      ...items.filter(i => i.local_id !== item.local_id),
      { ...draft, state: "draft" as const },
    ]);
    navigation.goBack();
  };

  const discard = async () => {
    if (!accessContext.userId || !accessContext.tenantId) return;
    const items = await loadQueue(accessContext.userId, accessContext.tenantId);
    await saveQueue(accessContext.userId, accessContext.tenantId, items.filter(i => i.local_id !== item.local_id));
    navigation.goBack();
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Sync conflict" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <InlineAlert tone="danger" title={copy.title} message={copy.message} />
        </Section>
        <Section>
          <SectionHeader title="Why automatic sync stopped" />
          <Card>
            <AppText color="secondary">ServiceOS never overwrites a newer server version automatically. Choose how to proceed below.</AppText>
          </Card>
        </Section>
        <Section>
          <SectionHeader title="Available resolution" />
          {item.job_id ? (
            <SecondaryButton
              label="View current version"
              onPress={() => {
                const parent = navigation.getParent();
                (parent?.navigate as (name: string, params?: object) => void)?.("JobExecutionStack", { screen: "JobDetail", params: { jobId: item.job_id } });
              }}
              style={{ marginBottom: theme.spacing.xs }}
              fullWidth
            />
          ) : null}
          <SecondaryButton label="Save my notes as a new draft" onPress={saveAsNewDraft} style={{ marginBottom: theme.spacing.xs }} fullWidth />
          <DestructiveButton label="Discard local draft" onPress={discard} fullWidth />
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
