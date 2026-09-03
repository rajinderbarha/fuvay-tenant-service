import { useEffect, useState } from "react";
import { AppNavigationSnapshot, AuthNavigationStatus, AccountAccessStatus } from "./guards/types";
import { useNetworkStatus } from "../hooks/useNetworkStatus";
import { getSecureItem } from "../storage/secureStorage";
import { getSessionSnapshot, subscribeSessionSnapshot, SessionSnapshot } from "../api/session/sessionEvents";
import { restoreSession } from "../api/session/sessionManager";
import { SessionState } from "../api/session/sessionStateMachine";
import { CustomerPublicAppConfig, isVersionBelow, loadCustomerPublicAppConfig } from "../api/appConfig/publicAppConfig";

const CURRENT_APP_VERSION = "1.0.0";

/**
 * Builds the live `AppNavigationSnapshot` the Phase E resolver consumes
 * (spec section 28: "Phase E navigation integration"). Bootstrap is only
 * ever marked `ready` once the session state machine has left
 * `uninitialized`/`restoring` and reached a TERMINAL state for this tick
 * (authenticated, unauthenticated, session_expired, invalid_audience,
 * account_suspended, or fatal_error) -- this is what guarantees no
 * authenticated flash: RootNavigator renders `PreparingExperienceScreen`
 * directly (not via the resolver) for as long as bootstrap stays
 * non-ready, so `resolveDestination` is never even called with a
 * still-resolving auth value.
 *
 * App version, maintenance state and enabled verticals come from the public
 * bootstrap endpoint. A failed config fetch routes to the API-unavailable
 * state instead of silently assuming that booking is safe to enter.
 */
const RESOLVING_STATES: readonly SessionState[] = ["uninitialized", "restoring"];

export function mapAuthStatus(state: SessionState): AuthNavigationStatus {
  switch (state) {
    case "authenticated":
    case "refreshing":
      return "authenticated_customer";
    case "session_expired":
      return "session_expired";
    case "invalid_audience":
      return "invalid_audience";
    case "unauthenticated":
    case "authenticating":
    case "mfa_required":
    case "network_degraded":
    case "fatal_error":
    case "account_suspended":
      return "unauthenticated";
    default:
      return "unknown";
  }
}

export function mapAccountStatus(state: SessionState, snapshot: SessionSnapshot): AccountAccessStatus {
  if (state === "account_suspended") return "suspended";
  return snapshot.context?.accountStatus === "suspended" || snapshot.context?.accountStatus === "blocked"
    ? "suspended"
    : "active";
}

export function useNavigationSnapshot(): AppNavigationSnapshot {
  const [sessionSnapshot, setSessionSnapshot] = useState<SessionSnapshot>(getSessionSnapshot());
  const [storageOk, setStorageOk] = useState<boolean | null>(null);
  const [appConfig, setAppConfig] = useState<CustomerPublicAppConfig | null>(null);
  const [configUnavailable, setConfigUnavailable] = useState(false);
  const network = useNetworkStatus();

  useEffect(() => {
    const unsubscribe = subscribeSessionSnapshot(setSessionSnapshot);
    if (getSessionSnapshot().state === "uninitialized") {
      restoreSession().catch(() => {});
    }
    return unsubscribe;
  }, []);

  useEffect(() => {
    let mounted = true;
    loadCustomerPublicAppConfig()
      .then(config => { if (mounted) setAppConfig(config); })
      .catch(() => { if (mounted) setConfigUnavailable(true); });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    getSecureItem("customer_app_bootstrap_probe")
      .then(() => { if (mounted) setStorageOk(true); })
      .catch(() => { if (mounted) setStorageOk(false); });
    return () => { mounted = false; };
  }, []);

  const isResolving = RESOLVING_STATES.includes(sessionSnapshot.state) || storageOk === null || (!appConfig && !configUnavailable);

  return {
    // Deliberately reuses the exact "initializing" sentinel RootNavigator
    // checks for (see root/App.tsx wiring) -- resolveDestination() is
    // never invoked at all while this is "initializing", which is what
    // prevents auth="unknown" from ever reaching the resolver's
    // unauthenticated/unknown branch and flashing the public placeholder
    // before restoration finishes.
    bootstrap: configUnavailable ? "failed" : isResolving ? "initializing" : "ready",
    auth: mapAuthStatus(sessionSnapshot.state),
    audience: sessionSnapshot.context?.audience ?? null,
    account: mapAccountStatus(sessionSnapshot.state, sessionSnapshot),
    appVersion: appConfig && isVersionBelow(CURRENT_APP_VERSION, appConfig.minimumSupportedVersion) ? "update_required" : "supported",
    platform: appConfig?.maintenance ? "maintenance" : configUnavailable ? "api_unavailable" : "available",
    storage: storageOk === false ? "unavailable" : "available",
    network: network === "online" ? "online" : network === "offline" ? "offline" : "unknown",
    enabledVerticals: { enabled: (appConfig?.enabledVerticals ?? ["home_services"]) as never[] },
    pendingDeepLink: undefined,
  };
}
