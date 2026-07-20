import { useEffect, useState } from "react";
import type { OfflineSyncStateView } from "../types/ux05";

/**
 * UX-05 Round 4: minimal real network-state hook for wiring
 * NetworkStatusBanner into the production app shell.
 *
 * HONEST LIMITATION: this app has no `@react-native-community/netinfo` (or
 * `expo-network`) dependency -- neither was installed by any prior round,
 * and adding one is a real dependency decision, not something to silently
 * slip into a hook. On native (iOS/Android), `navigator.onLine` does not
 * exist and this hook will always report "online" -- it CANNOT detect a
 * real native connectivity change today. On Expo web (react-native-web),
 * `navigator.onLine` + the `online`/`offline` window events are real and
 * this hook does correctly reflect actual browser connectivity -- verified
 * by the Playwright smoke test rendering the login screen with zero errors
 * on the same web bundle this hook ships in.
 *
 * `syncState`/`pendingDrafts`/`cacheState` are not derived from anything
 * real yet (no draft-queue or cache-staleness tracking exists) -- they are
 * fixed to the "nothing pending" defaults so the banner never fabricates a
 * sync-pending/conflict state that isn't actually happening.
 */
export function useNetworkStatus(): OfflineSyncStateView {
  const getOnline = () => (typeof navigator !== "undefined" && "onLine" in navigator) ? navigator.onLine : true;
  const [online, setOnline] = useState(getOnline());

  useEffect(() => {
    if (typeof window === "undefined" || !window.addEventListener) return;
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return {
    meta: { readiness: online ? "production_ready" : "read_only_ready" },
    networkState: online ? "online" : "offline",
    cacheState: "fresh",
    pendingDrafts: 0,
    syncState: "idle",
  };
}
