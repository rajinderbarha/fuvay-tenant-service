import { useCallback, useEffect, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useSession } from "../../navigation/session/SessionProvider";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { QueueItem } from "../../services/sync/types";
import { loadQueue, saveQueue } from "../../services/sync/queueStorage";
import { runSyncPass, SyncSummary } from "../../services/sync/syncEngine";
import { executeQueueItem } from "../../services/sync/syncApi";
import { onReconnect } from "../../services/api/networkState";

export interface SyncMetrics { synced: number; uploading: number; waiting: number; failed: number }
export type SyncFilter = "all" | "pending" | "failed";

const RECENT_WINDOW_MS = 24 * 60 * 60_000;

function scope(accessContext: { userId?: string; tenantId?: string }): { userId: string; tenantId: string } | null {
  if (!accessContext.userId || !accessContext.tenantId) return null;
  return { userId: accessContext.userId, tenantId: accessContext.tenantId };
}

/**
 * Composes the persisted queue + live network state into the Offline &
 * Sync Center's view model (Phase Z spec section 4). Never claims a
 * queue item is synced/confirmed beyond what's actually in local
 * storage -- there is no fabricated optimistic state here.
 */
export function useSyncCenter() {
  const { accessContext, networkStatus: sessionNetworkStatus } = useSession();
  const liveNetworkStatus = useNetworkStatus();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [filter, setFilter] = useState<SyncFilter>("all");
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  const scopeIds = scope(accessContext);

  const refresh = useCallback(async () => {
    if (!scopeIds) return;
    setItems(await loadQueue(scopeIds.userId, scopeIds.tenantId));
  }, [scopeIds?.userId, scopeIds?.tenantId]);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

  useEffect(() => onReconnect(() => { refresh(); }), [refresh]);

  const removeItem = useCallback(async (localId: string) => {
    if (!scopeIds) return;
    const next = items.filter(i => i.local_id !== localId);
    await saveQueue(scopeIds.userId, scopeIds.tenantId, next);
    setItems(next);
  }, [items, scopeIds?.userId, scopeIds?.tenantId]);

  const syncAllNow = useCallback(async (): Promise<SyncSummary | null> => {
    if (!scopeIds || isSyncing) return null;
    setIsSyncing(true);
    try {
      const summary = await runSyncPass(scopeIds.userId, scopeIds.tenantId, executeQueueItem);
      await refresh();
      setLastSyncedAt(new Date().toISOString());
      return summary;
    } finally {
      setIsSyncing(false);
    }
  }, [scopeIds?.userId, scopeIds?.tenantId, isSyncing, refresh]);

  const now = Date.now();
  const metrics: SyncMetrics = {
    synced: items.filter(i => i.state === "server_confirmed").length,
    uploading: items.filter(i => i.state === "uploading").length,
    waiting: items.filter(i => i.state === "waiting" || i.state === "draft").length,
    failed: items.filter(i => i.state === "failed" || i.state === "conflict" || i.state === "blocked").length,
  };

  const syncingNow = items.filter(i => i.state === "uploading");
  const waiting = items.filter(i => i.state === "waiting" || i.state === "draft");
  const needsAttention = items.filter(i => i.state === "conflict" || i.state === "failed" || i.state === "blocked" || i.state === "authentication_required");
  const recentlySynced = items
    .filter(i => i.state === "server_confirmed" && now - new Date(i.updated_at).getTime() < RECENT_WINDOW_MS)
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

  const filteredCounts = { all: items.length, pending: metrics.waiting + metrics.uploading, failed: metrics.failed };

  // API-reachability vs raw device connectivity (spec section 7) -- the
  // session provider's networkStatus already reflects NetInfo; a distinct
  // "server unreachable while device is online" state is surfaced by the
  // health probe elsewhere (Home screen banner), not duplicated here.
  const connectionState: "online" | "offline" | "limited" =
    liveNetworkStatus.networkState === "online" ? "online"
    : liveNetworkStatus.networkState === "slow" ? "limited"
    : liveNetworkStatus.networkState === "offline" ? "offline"
    : sessionNetworkStatus === "online" ? "online" : "offline";

  return {
    items, metrics, filter, setFilter, filteredCounts,
    syncingNow, waiting, needsAttention, recentlySynced,
    connectionState, isSyncing, syncAllNow, removeItem, refresh, lastSyncedAt,
  };
}
