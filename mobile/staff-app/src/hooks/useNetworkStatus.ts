import { useEffect, useState } from "react";
import NetInfo from "@react-native-community/netinfo";
import type { OfflineSyncStateView } from "../types/ux05";

/**
 * UX-05 Round 5: real network-state hook using @react-native-community/
 * netinfo (added this round -- investigated per the coordinator's request:
 * peer deps are permissive (`react: "*"`, `react-native: ">=0.59"`),
 * installed cleanly against this app's RN 0.85 with no conflicts, and
 * NetInfo has its own web implementation (uses the same underlying
 * `navigator.onLine`/connection APIs Round 4's hand-rolled hook used) --
 * so this single hook now covers native AND web with one real dependency
 * instead of a web-only DIY implementation.
 *
 * Supersedes Round 4's `navigator.onLine`-only version, which only worked
 * on Expo web and always reported "online" on native.
 *
 * `syncState`/`pendingDrafts`/`cacheState` are still not derived from
 * anything real (no draft-queue or cache-staleness tracking exists) --
 * fixed to "nothing pending" defaults so the banner never fabricates a
 * sync-pending/conflict state that isn't actually happening.
 */
export function useNetworkStatus(): OfflineSyncStateView {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setOnline(state.isConnected !== false && state.isInternetReachable !== false);
    });
    NetInfo.fetch().then(state => {
      setOnline(state.isConnected !== false && state.isInternetReachable !== false);
    });
    return () => unsubscribe();
  }, []);

  // "slow" is not derivable from NetInfo's basic state without also reading
  // `state.details.cellularGeneration`/effective-type, which varies wildly
  // by platform and wasn't verified this round -- left as a real gap rather
  // than guessed at. `isInternetReachable === false` with `isConnected ===
  // true` (device has a network interface but no real internet) is
  // presented as offline, not a fabricated "slow" state.
  return {
    meta: { readiness: "production_ready" },
    networkState: online ? "online" : "offline",
    cacheState: "fresh",
    pendingDrafts: 0,
    syncState: "idle",
  };
}
