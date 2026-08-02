import React from "react";
import { View, ScrollView, Pressable } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section, Inline } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { IconButton } from "../../design-system/components/actions/IconButton";
import { SecondaryButton } from "../../design-system/components/actions/Buttons";
import { SegmentedControl } from "../../design-system/components/forms/SegmentedControl";
import { MetricCard } from "../../design-system/components/data-display/MetricCard";
import { ProgressBar } from "../../design-system/components/feedback/Loading";
import { InlineAlert } from "../../design-system/components/feedback/Banner";
import { EmptyState } from "../../design-system/components/feedback/States";
import { Icon } from "../../design-system/components/Icon";
import { useSyncCenter, SyncFilter } from "./useSyncCenter";
import { QueueItem } from "../../services/sync/types";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "OfflineSyncCenter">;

const CONNECTION_COPY: Record<string, { title: string; icon: "cloud-done-outline" | "cloud-offline-outline" | "warning-outline"; tone: "success" | "danger" | "warning" }> = {
  online: { title: "You're online", icon: "cloud-done-outline", tone: "success" },
  offline: { title: "You're offline", icon: "cloud-offline-outline", tone: "danger" },
  limited: { title: "Limited connection", icon: "warning-outline", tone: "warning" },
};

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  return `${hours} hr ago`;
}

function SyncRow({ item, onPress }: { item: QueueItem; onPress: () => void }) {
  const { theme } = useTheme();
  const icon = item.operation_class === "MEDIA_UPLOAD" ? "image-outline" : "document-text-outline";
  const isConflict = item.state === "conflict";
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${item.title}. ${item.job_reference ?? ""}`}>
      <View style={{
        flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm,
        borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle, gap: theme.spacing.sm,
        borderColor: isConflict ? theme.colors.statusDanger : undefined,
        borderWidth: isConflict ? 1 : 0, borderRadius: isConflict ? theme.radiusUsage.card : 0,
        padding: isConflict ? theme.spacing.sm : undefined,
        backgroundColor: isConflict ? theme.colors.statusDangerSurface : undefined,
      }}>
        <View style={{
          width: 40, height: 40, borderRadius: theme.radiusUsage.avatar, alignItems: "center", justifyContent: "center",
          backgroundColor: theme.colors.surfaceInteractive,
        }}>
          <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">{item.title}</AppText>
          {item.job_reference ? <AppText variant="caption" color="tertiary">{item.job_reference}</AppText> : null}
          {item.state === "conflict" ? <AppText variant="caption" style={{ color: theme.colors.statusDanger }}>A newer version exists on the server</AppText> : null}
          {item.state === "waiting" && item.next_attempt_at ? <AppText variant="caption" color="tertiary">Waiting for Wi-Fi</AppText> : null}
        </View>
        {item.state === "conflict" ? (
          <SecondaryButton label="Review" onPress={onPress} />
        ) : item.state === "uploading" ? (
          <AppText variant="caption" color="link">In progress</AppText>
        ) : item.state === "server_confirmed" ? (
          <AppText variant="caption" color="tertiary">{relativeTime(item.updated_at)}</AppText>
        ) : null}
      </View>
    </Pressable>
  );
}

export function OfflineSyncCenterScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const {
    metrics, filter, setFilter, filteredCounts, syncingNow, waiting, needsAttention,
    recentlySynced, connectionState, isSyncing, syncAllNow, lastSyncedAt,
  } = useSyncCenter();

  const connCopy = CONNECTION_COPY[connectionState] ?? CONNECTION_COPY.offline;

  const filterOptions: { value: SyncFilter; label: string }[] = [
    { value: "all", label: `All  ${filteredCounts.all}` },
    { value: "pending", label: `Pending  ${filteredCounts.pending}` },
    { value: "failed", label: `Failed  ${filteredCounts.failed}` },
  ];

  const groupsForFilter = () => {
    if (filter === "failed") return { syncingNow: [], waiting: [], needsAttention, recentlySynced: [] };
    if (filter === "pending") return { syncingNow, waiting, needsAttention: [], recentlySynced: [] };
    return { syncingNow, waiting, needsAttention, recentlySynced };
  };
  const groups = groupsForFilter();
  const isEmpty = groups.syncingNow.length + groups.waiting.length + groups.needsAttention.length + groups.recentlySynced.length === 0;

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: theme.spacing.sm, height: 52 }}>
        <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={() => navigation.goBack()} />
        <AppText variant="bodyStrong" style={{ flex: 1, textAlign: "center" }}>Offline & sync</AppText>
        <IconButton icon="refresh-outline" accessibilityLabel="Sync now" loading={isSyncing} onPress={async () => { await syncAllNow(); }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card>
            <Inline justify="space-between">
              <Inline gap="sm">
                <Icon name={connCopy.icon} size="compact" color={connCopy.tone === "success" ? theme.colors.statusSuccess : connCopy.tone === "danger" ? theme.colors.statusDanger : theme.colors.statusWarning} decorative />
                <View>
                  <AppText variant="bodyStrong">{connCopy.title}</AppText>
                  <AppText variant="caption" color="tertiary">Last synced {lastSyncedAt ? relativeTime(lastSyncedAt) : "just now"}</AppText>
                </View>
              </Inline>
              <View style={{ paddingHorizontal: theme.spacing.sm, paddingVertical: 4, borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.statusSuccessSurface }}>
                <AppText variant="labelStrong" style={{ color: theme.colors.statusSuccess }}>{connectionState === "online" ? "Connected" : connectionState === "limited" ? "Limited" : "Offline"}</AppText>
              </View>
            </Inline>
          </Card>
        </Section>

        <Section>
          <Inline gap="sm">
            <MetricCard label="Synced" value={String(metrics.synced)} tone="success" icon="checkmark-circle-outline" />
            <MetricCard label="Uploading" value={String(metrics.uploading)} tone="neutral" icon="cloud-upload-outline" />
            <MetricCard label="Waiting" value={String(metrics.waiting)} tone="warning" icon="time-outline" />
            <MetricCard label="Failed" value={String(metrics.failed)} tone="danger" icon="alert-circle-outline" />
          </Inline>
        </Section>

        <Section>
          <SegmentedControl options={filterOptions} value={filter} onChange={setFilter} />
        </Section>

        {isEmpty ? (
          <EmptyState icon="checkmark-done-outline" title="Nothing pending" message="All your work is synced with ServiceOS." />
        ) : (
          <>
            {groups.syncingNow.length > 0 ? (
              <Section>
                <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>Syncing now</AppText>
                <Card>{groups.syncingNow.map(item => <SyncRow key={item.local_id} item={item} onPress={() => navigation.navigate("SyncItemDetail", { localId: item.local_id })} />)}</Card>
              </Section>
            ) : null}
            {groups.waiting.length > 0 ? (
              <Section>
                <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>Waiting</AppText>
                <Card>{groups.waiting.map(item => <SyncRow key={item.local_id} item={item} onPress={() => navigation.navigate("SyncItemDetail", { localId: item.local_id })} />)}</Card>
              </Section>
            ) : null}
            {groups.needsAttention.length > 0 ? (
              <Section>
                <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>Needs attention</AppText>
                {groups.needsAttention.map(item => (
                  <View key={item.local_id} style={{ marginBottom: theme.spacing.sm }}>
                    <SyncRow item={item} onPress={() => navigation.navigate(item.state === "conflict" ? "SyncConflictReview" : "SyncItemDetail", { localId: item.local_id })} />
                  </View>
                ))}
              </Section>
            ) : null}
            {groups.recentlySynced.length > 0 ? (
              <Section>
                <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>Recently synced</AppText>
                <Card>{groups.recentlySynced.map(item => <SyncRow key={item.local_id} item={item} onPress={() => navigation.navigate("SyncItemDetail", { localId: item.local_id })} />)}</Card>
              </Section>
            ) : null}
          </>
        )}

        <Section>
          <InlineAlert tone="info" title="How this works" message="Job actions are submitted only after the server confirms them. Photos and drafts stay encrypted on this device until synced." />
        </Section>

        <SecondaryButton
          label="Sync all now"
          leadingIcon={<Icon name="cloud-upload-outline" size="compact" color={theme.colors.textPrimary} decorative />}
          onPress={async () => { await syncAllNow(); }}
          loading={isSyncing}
          disabled={isSyncing || connectionState === "offline"}
          fullWidth
        />
        <View style={{ marginTop: theme.spacing.base, alignItems: "center" }}>
          <AppText variant="caption" color="tertiary" onPress={() => navigation.navigate("OfflineStorage")}>
            Offline data: <AppText variant="caption" color="link">Manage storage</AppText>
          </AppText>
        </View>
      </ScrollView>
    </SafeAreaScreen>
  );
}
