import React, { useEffect, useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { DestructiveButton, SecondaryButton } from "../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { useSession } from "../../navigation/session/SessionProvider";
import { loadQueue, saveQueue } from "../../services/sync/queueStorage";
import { QueueItem } from "../../services/sync/types";
import { getIdempotencyStatus } from "../../services/sync/syncApi";

type Props = NativeStackScreenProps<ProfileStackParamList, "SyncItemDetail">;

const STATE_LABEL: Record<string, string> = {
  draft: "Saved on this device", waiting: "Waiting to sync", uploading: "Uploading",
  submitted: "Submitted", server_confirmed: "Server confirmed", failed: "Failed",
  conflict: "Conflict", blocked: "Blocked", cancelled: "Cancelled",
  authentication_required: "Sign-in required",
};

/**
 * Item detail (Phase Z spec section 4). Shows only safe, human-readable
 * metadata -- never a raw payload dump -- plus, when the outcome is
 * genuinely unknown (last attempt uploading/failed after a dropped
 * connection), a real idempotency-status lookup rather than guessing.
 */
export function SyncItemDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { accessContext } = useSession();
  const [item, setItem] = useState<QueueItem | null>(null);
  const [checking, setChecking] = useState(false);
  const [outcome, setOutcome] = useState<"confirmed" | "unknown" | null>(null);

  useEffect(() => {
    if (!accessContext.userId || !accessContext.tenantId) return;
    loadQueue(accessContext.userId, accessContext.tenantId).then(items => {
      setItem(items.find(i => i.local_id === route.params.localId) ?? null);
    });
  }, [accessContext.userId, accessContext.tenantId, route.params.localId]);

  const checkOutcome = async () => {
    if (!item) return;
    setChecking(true);
    const result = await getIdempotencyStatus(item.idempotency_key, `sync:${item.operation_type}`);
    setChecking(false);
    if (result.ok) setOutcome(result.data.status);
  };

  const discard = async () => {
    if (!item || !accessContext.userId || !accessContext.tenantId) return;
    const items = await loadQueue(accessContext.userId, accessContext.tenantId);
    await saveQueue(accessContext.userId, accessContext.tenantId, items.filter(i => i.local_id !== item.local_id));
    navigation.goBack();
  };

  if (!item) {
    return (
      <SafeAreaScreen edges={["top", "left", "right"]}>
        <ScreenHeader title="Sync item" onBack={() => navigation.goBack()} />
        <View style={{ padding: theme.spacing.lg }}>
          <AppText color="secondary">This item is no longer in the queue.</AppText>
        </View>
      </SafeAreaScreen>
    );
  }

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title={item.title} onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <SectionHeader title="Status" />
          <Card>
            <KeyValueList items={[
              { label: "State", value: STATE_LABEL[item.state] ?? item.state },
              { label: "Job reference", value: item.job_reference ?? "—" },
              { label: "Attempts", value: String(item.attempt_count) },
              { label: "Last updated", value: new Date(item.updated_at).toLocaleString() },
            ]} />
          </Card>
        </Section>

        {(item.state === "uploading" || item.state === "failed") ? (
          <Section>
            <InlineAlert
              tone="warning"
              title="Confirmation pending"
              message="If this action started before your connection dropped, do not repeat it. Check its real outcome first."
            />
            <View style={{ marginTop: theme.spacing.sm }}>
              <SecondaryButton label="Check outcome" onPress={checkOutcome} loading={checking} />
            </View>
            {outcome === "confirmed" ? <AppText style={{ color: theme.colors.statusSuccess, marginTop: theme.spacing.xs }}>Confirmed by the server -- safe to remove from the queue.</AppText> : null}
            {outcome === "unknown" ? <AppText color="tertiary" style={{ marginTop: theme.spacing.xs }}>Still unknown -- it will keep retrying automatically.</AppText> : null}
          </Section>
        ) : null}

        {item.state === "failed" || item.state === "cancelled" ? (
          <Section>
            <DestructiveButton label="Discard this item" onPress={discard} fullWidth />
          </Section>
        ) : null}
      </ScrollView>
    </SafeAreaScreen>
  );
}
