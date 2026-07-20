import { useEffect, useState } from "react";

export type ConnectivityStatus = "online" | "offline" | "unknown";

export interface ConnectivityState {
  status: ConnectivityStatus;
}

/**
 * Network-state abstraction. Ships without a hard dependency on
 * @react-native-community/netinfo (not present in the repo and not required
 * for this sprint's scope) — uses a lightweight reachability probe so later
 * sprints can swap in NetInfo behind this same hook without call-site churn.
 */
export function useConnectivity(): ConnectivityState {
  const [status, setStatus] = useState<ConnectivityStatus>("unknown");

  useEffect(() => {
    let cancelled = false;

    async function probe() {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4000);
        await fetch("https://clients3.google.com/generate_204", { method: "HEAD", signal: controller.signal });
        clearTimeout(timeout);
        if (!cancelled) setStatus("online");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    void probe();
    const interval = setInterval(probe, 15_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return { status };
}
