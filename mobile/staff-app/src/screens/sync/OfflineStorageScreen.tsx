import React, { useMemo, useState } from "react";
import { View, ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { SectionHeader, KeyValueList } from "../../design-system/components/data-display/InfoRow";
import { AppText } from "../../design-system/components/typography/AppText";
import { DestructiveButton } from "../../design-system/components/actions/Buttons";
import { ConfirmationDialog } from "../../design-system/components/overlays/ConfirmationDialog";
import { ScreenHeader } from "../profile/components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";
import { useSyncCenter } from "./useSyncCenter";
import { useSession } from "../../navigation/session/SessionProvider";
import { loadQueue, saveQueue } from "../../services/sync/queueStorage";

type Props = NativeStackScreenProps<ProfileStackParamList, "OfflineStorage">;

/**
 * Offline Storage (Phase Z spec section 19). Only ever removes LOCAL
 * COPIES of already server-confirmed items -- an unsynced draft, a
 * pending upload, or anything referenced by an active queue item is
 * never deleted here, and there is no unscoped "Clear all" (spec's
 * explicit non-goal).
 */
export function OfflineStorageScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const { accessContext } = useSession();
  const { items, recentlySynced, refresh } = useSyncCenter();
  const [confirming, setConfirming] = useState(false);

  const pendingCount = items.filter(i => i.state !== "server_confirmed" && i.state !== "cancelled").length;
  const approxBytes = useMemo(() => JSON.stringify(items).length, [items]);
  const approxMb = (approxBytes / (1024 * 1024)).toFixed(2);

  const clearConfirmedCopies = async () => {
    if (!accessContext.userId || !accessContext.tenantId) return;
    const remaining = (await loadQueue(accessContext.userId, accessContext.tenantId)).filter(i => i.state !== "server_confirmed");
    await saveQueue(accessContext.userId, accessContext.tenantId, remaining);
    setConfirming(false);
    await refresh();
  };

  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Offline storage" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <SectionHeader title="Usage on this device" />
          <Card>
            <KeyValueList items={[
              { label: "Total offline data", value: `${approxMb} MB` },
              { label: "Pending items (never deleted here)", value: String(pendingCount) },
              { label: "Confirmed-upload local copies", value: String(recentlySynced.length) },
            ]} />
          </Card>
        </Section>

        <Section>
          <AppText color="secondary">
            Removing confirmed-upload local copies frees space without affecting anything still pending or unsynced.
            Drafts, pending uploads, and anything a queued item still needs are never removed here.
          </AppText>
        </Section>

        <Section>
          <DestructiveButton
            label="Remove confirmed-upload local copies"
            onPress={() => setConfirming(true)}
            disabled={recentlySynced.length === 0}
            fullWidth
          />
        </Section>
      </ScrollView>

      <ConfirmationDialog
        visible={confirming}
        title="Remove local copies?"
        message={`This removes ${recentlySynced.length} already-confirmed item${recentlySynced.length === 1 ? "" : "s"} from this device. Nothing pending or unsynced is affected.`}
        confirmLabel="Remove"
        onConfirm={clearConfirmedCopies}
        onCancel={() => setConfirming(false)}
        destructive
      />
    </SafeAreaScreen>
  );
}
