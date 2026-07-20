import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { Platform, AppState, type AppStateStatus } from "react-native";
import { useConnectivity } from "../../hooks/useConnectivity";
import { runStartup, retryStartup, getStartupSnapshot, subscribeStartup } from "./startup-service";
import type { StartupSnapshot } from "./startup-types";

interface StartupContextValue {
  snapshot: StartupSnapshot;
  retry: () => void;
}

const StartupContext = createContext<StartupContextValue | null>(null);

const RESUME_REEVALUATION_MIN_INTERVAL_MS = 60_000;

export function StartupProvider({ children }: { children: React.ReactNode }) {
  const { status: connectivityStatus } = useConnectivity();
  const [snapshot, setSnapshot] = useState<StartupSnapshot>(getStartupSnapshot());
  const hasStartedRef = useRef(false);
  const lastResumeCheckRef = useRef<number>(0);

  useEffect(() => subscribeStartup(setSnapshot), []);

  useEffect(() => {
    if (hasStartedRef.current) return;
    // Wait for a definitive connectivity read (not "unknown") before running
    // startup once — but don't wait forever; "unknown" degrades gracefully
    // inside the resolver rather than blocking the very first run indefinitely.
    hasStartedRef.current = true;
    lastResumeCheckRef.current = Date.now();
    void runStartup({ connectivity: connectivityStatus, platform: Platform.OS === "ios" ? "ios" : "android" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState: AppStateStatus) => {
      if (nextState !== "active") return;
      const now = Date.now();
      if (now - lastResumeCheckRef.current < RESUME_REEVALUATION_MIN_INTERVAL_MS) return;
      lastResumeCheckRef.current = now;
      if (snapshot.status === "ready" || snapshot.status === "degraded") {
        void retryStartup({ connectivity: connectivityStatus, platform: Platform.OS === "ios" ? "ios" : "android" });
      }
    });
    return () => subscription.remove();
  }, [connectivityStatus, snapshot.status]);

  const retry = useCallback(() => {
    void retryStartup({ connectivity: connectivityStatus, platform: Platform.OS === "ios" ? "ios" : "android" });
  }, [connectivityStatus]);

  return <StartupContext.Provider value={{ snapshot, retry }}>{children}</StartupContext.Provider>;
}

export function useStartupContext(): StartupContextValue {
  const ctx = useContext(StartupContext);
  if (!ctx) throw new Error("useStartupContext must be used within a StartupProvider");
  return ctx;
}
