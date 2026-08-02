import React, { createContext, useContext, useEffect, useMemo, useState, useCallback, useRef } from "react";
import Constants from "expo-constants";
import { AppState, AppStateStatus } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { AccessContext, BootstrapState, ReasonCode, UNAUTHENTICATED_CONTEXT } from "../guards/types";
import { resolveNavigationState, destinationForBootstrapState } from "../guards/resolveNavigationState";
import { SessionAdapter, secureStoreSessionAdapter } from "./SessionAdapter";
import { resetRoot } from "../navigationRef";
import { subscribeSessionEvents } from "../../services/auth/sessionEvents";
import { startNetworkMonitoring, subscribeNetworkState, onReconnect } from "../../services/api/networkState";
import * as sessionManager from "../../services/auth/sessionManager";
import { NetworkState } from "../../services/api/types";

const FOREGROUND_REVALIDATE_THRESHOLD_MS = 60_000;

const CURRENT_APP_VERSION = Constants.expoConfig?.version ?? "0.0.0";

interface SessionContextValue {
  bootstrapState: BootstrapState;
  reasonCode?: ReasonCode;
  accessContext: AccessContext;
  /** Full protected-state reset (spec section 10/12): cancels/removes
   * sensitive query cache, clears stored session via the adapter, resets
   * navigation to AuthStack. Used for logout and for session invalidation
   * detected while a protected screen is open. */
  invalidateSession: () => Promise<void>;
  /** Phase F auth work sets the freshly-authenticated context through this
   * boundary -- this phase never calls it itself (no login exists yet). */
  setAccessContext: (context: AccessContext) => void;
  /** Real Phase F session actions (spec sections 6, 19) -- thin wrappers
   * over services/auth/sessionManager, exposed here so future Login/
   * Profile/Settings screens never import the service layer directly. */
  revokeCurrentSession: () => Promise<void>;
  revokeAllSessions: () => Promise<{ remoteConfirmed: boolean; sessionsRevoked?: number }>;
  establishSession: (authResult: { access_token: string; refresh_token: string | null }) => Promise<void>;
  consumePendingDestination: () => string | null;
  networkStatus: NetworkState;
  retryBootstrap: () => Promise<void>;
  /** The last authenticated user/tenant scope seen before the CURRENT
   * accessContext (which may since be cleared/unauthenticated). Exists
   * only so the "please sign in again" screen can look up how many real,
   * already-persisted offline-queue drafts are still safe on this device
   * for the technician who just got signed out -- never used to resume a
   * session or re-authorize anything. */
  lastKnownScope: { userId: string; tenantId: string } | null;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export interface SessionProviderProps {
  children: React.ReactNode;
  /** Injectable for tests/dev fixtures; defaults to the real SecureStore adapter. */
  adapter?: SessionAdapter;
}

export function SessionProvider({ children, adapter = secureStoreSessionAdapter }: SessionProviderProps) {
  const queryClient = useQueryClient();
  const [isRestoring, setIsRestoring] = useState(true);
  const [accessContext, setAccessContextState] = useState<AccessContext>(UNAUTHENTICATED_CONTEXT);
  const [networkStatus, setNetworkStatus] = useState<NetworkState>("unknown");
  const lastValidatedAtRef = useRef<number>(0);
  const reconnectInFlightRef = useRef(false);
  const lastKnownScopeRef = useRef<{ userId: string; tenantId: string } | null>(null);

  // Captured on every authenticated render BEFORE a subsequent clear -- by
  // the time invalidateSession() has run, this ref still holds the scope
  // that was just cleared (a plain state field would already be wiped).
  useEffect(() => {
    if (accessContext.authenticated && accessContext.userId && accessContext.tenantId) {
      lastKnownScopeRef.current = { userId: accessContext.userId, tenantId: accessContext.tenantId };
    }
  }, [accessContext.authenticated, accessContext.userId, accessContext.tenantId]);

  // Only the real production adapter drives events/network/lifecycle --
  // a fixture adapter (tests/dev) is a deliberately hermetic, one-shot
  // snapshot with no ongoing behavior, so it must never start timers,
  // NetInfo listeners, or AppState subscriptions.
  const isProductionAdapter = adapter === secureStoreSessionAdapter;

  const runRestore = useCallback(async (mountedRef: { current: boolean }) => {
    const restored = await adapter.restoreSession();
    if (!mountedRef.current) return;
    setAccessContextState(restored);
    setIsRestoring(false);
    lastValidatedAtRef.current = Date.now();
  }, [adapter]);

  useEffect(() => {
    const mountedRef = { current: true };
    runRestore(mountedRef);
    return () => { mountedRef.current = false; };
  }, [runRestore]);

  /** Re-runs the exact same restore sequence used on cold start (Phase G
   * spec section 10: the "Retry" action on restricted-state screens --
   * re-checking current backend/tenant/technician state, not merely
   * dismissing the screen). Does not flip isRestoring back to true, since
   * this is a background re-check, not a fresh app boot -- the current
   * (possibly restricted) screen stays visible until the result is known. */
  const retryBootstrap = useCallback(async () => {
    const mountedRef = { current: true };
    await runRestore(mountedRef);
  }, [runRestore]);

  const { state: bootstrapState, reasonCode } = useMemo(
    () => resolveNavigationState({
      bootstrapPhase: isRestoring ? "initializing" : "restored",
      accessContext,
      currentAppVersion: CURRENT_APP_VERSION,
    }),
    [isRestoring, accessContext],
  );

  const invalidateSession = useCallback(async () => {
    // Cancel + drop everything first so no protected data lingers in cache
    // for the instant between "session invalid" and "navigation reset".
    await queryClient.cancelQueries();
    queryClient.clear();
    await adapter.clearSession();
    setAccessContextState(UNAUTHENTICATED_CONTEXT);
    resetRoot({ index: 0, routes: [{ name: "AuthStack" }] });
  }, [adapter, queryClient]);

  const setAccessContext = useCallback((context: AccessContext) => {
    setAccessContextState(context);
  }, []);

  // ── Phase F: mid-session events (spec section 20) ───────────────────────
  useEffect(() => {
    if (!isProductionAdapter) return;
    return subscribeSessionEvents(event => {
      switch (event.type) {
        case "SESSION_ESTABLISHED":
        case "ACCESS_CONTEXT_CHANGED":
        case "ACCOUNT_RESTRICTED":
        case "TENANT_RESTRICTED":
        case "TECHNICIAN_RESTRICTED":
          setAccessContextState(event.accessContext);
          lastValidatedAtRef.current = Date.now();
          break;
        case "SESSION_EXPIRED":
        case "SESSION_REVOKED":
        case "SESSION_CLEARED":
          invalidateSession();
          break;
        default:
          break;
      }
    });
  }, [isProductionAdapter, invalidateSession]);

  // ── Phase F: network awareness + reconnect revalidation (spec section 15) ──
  useEffect(() => {
    if (!isProductionAdapter) return;
    startNetworkMonitoring();
    return subscribeNetworkState(setNetworkStatus);
  }, [isProductionAdapter]);

  useEffect(() => {
    if (!isProductionAdapter) return;
    return onReconnect(() => {
      if (reconnectInFlightRef.current || !accessContext.authenticated) return;
      reconnectInFlightRef.current = true;
      sessionManager.refreshAccessContext()
        .then(snapshot => setAccessContextState(snapshot.accessContext))
        .finally(() => { reconnectInFlightRef.current = false; });
    });
  }, [isProductionAdapter, accessContext.authenticated]);

  // ── Phase F: foreground revalidation (spec section 18) ──────────────────
  useEffect(() => {
    if (!isProductionAdapter) return;
    const handleChange = (next: AppStateStatus) => {
      if (next !== "active" || !accessContext.authenticated) return;
      if (Date.now() - lastValidatedAtRef.current < FOREGROUND_REVALIDATE_THRESHOLD_MS) return;
      sessionManager.refreshAccessContext().then(snapshot => {
        setAccessContextState(snapshot.accessContext);
        lastValidatedAtRef.current = Date.now();
      });
    };
    const sub = AppState.addEventListener("change", handleChange);
    return () => sub.remove();
  }, [isProductionAdapter, accessContext.authenticated]);

  const revokeCurrentSession = useCallback(async () => {
    await sessionManager.revokeCurrentSession();
    await invalidateSession();
  }, [invalidateSession]);

  const revokeAllSessions = useCallback(async () => {
    const result = await sessionManager.revokeAllSessions();
    await invalidateSession();
    return result;
  }, [invalidateSession]);

  const establishSession = useCallback(async (authResult: { access_token: string; refresh_token: string | null }) => {
    const result = await sessionManager.establishSession(authResult);
    setAccessContextState(result.accessContext);
    setIsRestoring(false);
    lastValidatedAtRef.current = Date.now();
  }, []);

  const consumePendingDestination = useCallback(() => sessionManager.consumePendingDestination(), []);

  const value = useMemo<SessionContextValue>(() => ({
    bootstrapState, reasonCode, accessContext, invalidateSession, setAccessContext,
    revokeCurrentSession, revokeAllSessions, establishSession, consumePendingDestination, networkStatus, retryBootstrap,
    lastKnownScope: lastKnownScopeRef.current,
  }), [bootstrapState, reasonCode, accessContext, invalidateSession, setAccessContext,
      revokeCurrentSession, revokeAllSessions, establishSession, consumePendingDestination, networkStatus, retryBootstrap]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within a SessionProvider");
  return ctx;
}

export function useRootDestination() {
  const { bootstrapState, reasonCode } = useSession();
  return useMemo(() => destinationForBootstrapState(bootstrapState, reasonCode), [bootstrapState, reasonCode]);
}
