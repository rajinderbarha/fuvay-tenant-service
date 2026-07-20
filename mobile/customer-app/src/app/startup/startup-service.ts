import { environment } from "../../config/environment";
import { logger } from "../../observability/logger";
import { loadCachedConfig, refreshRemoteConfig } from "../../remote-config/remote-config-service";
import { buildCompiledDefaults } from "../../remote-config/remote-config-defaults";
import type { ResolvedRemoteConfig } from "../../remote-config/remote-config-types";
import { consumePendingDestination } from "../../navigation/deep-links/pending-deep-link-store";
import { resolveDeepLink } from "../../navigation/deep-links/deep-link-resolver";
import { getInitialUrlOnce } from "../../navigation/deep-links/initial-url-bridge";
import type { AuthPlaceholderState, OnboardingPlaceholderState } from "../../navigation/route-guards";
import { bootstrapSession } from "../../features/auth/state/session-bootstrap";
import { resolveInitialRoute, type StartupRouteResolverInput } from "./startup-route-resolver";
import { startupReducer, createInitialStartupSnapshot, type StartupAction } from "./startup-machine";
import { STARTUP_TIMEOUTS_MS, withTimeout } from "./startup-timeouts";
import { StartupError } from "./startup-errors";
import { getStartupDevOverrides } from "./startup-dev-overrides";
import type { StartupSnapshot, StartupPhase } from "./startup-types";

export interface StartupRunInput {
  connectivity: "online" | "offline" | "unknown";
  platform: "ios" | "android";
  /** Placeholder only — real auth arrives in CUSTOMER-L5-02. Never "authenticated" from this sprint's own logic. */
  auth?: AuthPlaceholderState;
  onboarding?: OnboardingPlaceholderState;
}

let snapshot: StartupSnapshot = createInitialStartupSnapshot();
let activeSequenceId = 0;
let running = false;
let lastRunInput: StartupRunInput | null = null;
const listeners = new Set<(snapshot: StartupSnapshot) => void>();

function dispatch(action: StartupAction) {
  snapshot = startupReducer(snapshot, action);
  listeners.forEach((listener) => listener(snapshot));
}

export function getStartupSnapshot(): StartupSnapshot {
  return snapshot;
}

export function subscribeStartup(listener: (snapshot: StartupSnapshot) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

async function runPhase<T>(sequenceId: number, phase: StartupPhase, work: () => Promise<T>, timeoutMs?: number): Promise<T | undefined> {
  if (sequenceId !== activeSequenceId) return undefined; // superseded by a newer run
  dispatch({ type: "PHASE_STARTED", phase, at: new Date().toISOString() });
  try {
    const result = timeoutMs ? await withTimeout(work(), timeoutMs, `${phase} timed out`) : await work();
    if (sequenceId !== activeSequenceId) return undefined;
    dispatch({ type: "PHASE_COMPLETED", phase, at: new Date().toISOString(), result: "success" });
    return result;
  } catch (err) {
    if (sequenceId !== activeSequenceId) return undefined;
    const category = err instanceof Error && /timed out/.test(err.message) ? "timeout" : "unknown";
    dispatch({ type: "PHASE_FAILED", phase, at: new Date().toISOString(), category, retryAllowed: category === "timeout" });
    logger.warn("startup.phase_failed", { phase, category });
    throw err;
  }
}

/** Starts exactly one startup run. A concurrent call returns the same in-flight promise rather than starting a second run. */
export async function runStartup(input: StartupRunInput): Promise<StartupSnapshot> {
  lastRunInput = input;
  if (running) return waitForTerminalSnapshot();
  running = true;
  activeSequenceId += 1;
  const sequenceId = activeSequenceId;
  dispatch({ type: "RESET" });
  dispatch({ type: "CONNECTIVITY_RESOLVED", connectivity: input.connectivity });

  try {
    await runPhase(sequenceId, "initializing", async () => undefined);

    const environmentValid = await runPhase(
      sequenceId,
      "validating-environment",
      async () => environment.name !== undefined,
      STARTUP_TIMEOUTS_MS.environmentValidation
    );

    await runPhase(sequenceId, "loading-local-preferences", async () => undefined);
    const bootstrappedAuth =
      (await runPhase(sequenceId, "loading-secure-session-placeholder", () => bootstrapSession(), STARTUP_TIMEOUTS_MS.secureSessionPlaceholderRead).catch(
        () => "guest" as const
      )) ?? "guest";
    await runPhase(sequenceId, "resolving-locale", async () => undefined);
    await runPhase(sequenceId, "resolving-theme", async () => undefined);
    await runPhase(sequenceId, "checking-connectivity", async () => input.connectivity);

    let resolved: ResolvedRemoteConfig | undefined;
    await runPhase(sequenceId, "loading-cached-config", async () => {
      resolved = (await loadCachedConfig()) ?? undefined;
      return resolved;
    });

    let configSource: StartupRouteResolverInput["configSource"] = resolved ? resolved.source : "none";

    if (input.connectivity !== "offline") {
      try {
        const fresh = await runPhase(
          sequenceId,
          "fetching-remote-config",
          () => refreshRemoteConfig({ timeoutMs: STARTUP_TIMEOUTS_MS.remoteConfigFetch }),
          STARTUP_TIMEOUTS_MS.remoteConfigFetch
        );
        if (fresh) {
          resolved = fresh;
          configSource = fresh.source;
        }
      } catch {
        // Fetch failure is non-fatal here — fall through to whatever cache (or lack thereof) was already loaded.
      }
    }

    if (!resolved && configSource !== "none") {
      resolved = { config: buildCompiledDefaults(), source: "compiled-defaults", fetchedAt: new Date().toISOString() };
    }
    if (!resolved) {
      resolved = { config: buildCompiledDefaults(), source: "compiled-defaults", fetchedAt: new Date().toISOString() };
      configSource = "compiled-defaults";
    }

    dispatch({ type: "CONFIG_RESOLVED", config: resolved });

    // Dev-only simulation overrides — never active in a production bundle (see startup-dev-overrides.ts).
    const devOverrides = __DEV__ ? getStartupDevOverrides() : undefined;
    const effectiveConnectivity = devOverrides?.forceOffline ? "offline" : input.connectivity;
    const effectiveConfig =
      devOverrides?.forceMandatoryUpdate || devOverrides?.forceMaintenance
        ? {
            ...resolved.config,
            versionPolicy: devOverrides.forceMandatoryUpdate ? { ...resolved.config.versionPolicy, mandatoryUpdate: true } : resolved.config.versionPolicy,
            maintenance: devOverrides.forceMaintenance
              ? { ...resolved.config.maintenance, enabled: true, type: "active-blocking" as const }
              : resolved.config.maintenance,
          }
        : resolved.config;

    await runPhase(sequenceId, "evaluating-version-policy", async () => undefined);
    await runPhase(sequenceId, "evaluating-maintenance-policy", async () => undefined);
    await runPhase(sequenceId, "resolving-marketplace-context", async () => undefined);

    const auth = input.auth ?? bootstrappedAuth;
    const onboarding = input.onboarding ?? "skipped-where-allowed";
    await runPhase(sequenceId, "resolving-auth-placeholder", async () => auth);
    dispatch({ type: "AUTH_RESOLVED", auth });
    await runPhase(sequenceId, "resolving-onboarding-placeholder", async () => onboarding);
    dispatch({ type: "ONBOARDING_RESOLVED", onboarding });

    await runPhase(
      sequenceId,
      "resolving-deep-link",
      async () => {
        const initialUrl = devOverrides?.forceInvalidDeepLink ? "not-a-valid-url" : await getInitialUrlOnce();
        if (!initialUrl) return undefined;
        return resolveDeepLink(initialUrl, {
          startupReady: true,
          config: resolved!.config,
          maintenanceBlocking: false,
          versionMandatoryUpdate: false,
          marketplaceAvailable: true,
          auth,
          onboarding,
          isProductionBuild: environment.name === "production",
          isDevBuild: __DEV__,
          appVersion: environment.buildVersion,
        });
      },
      STARTUP_TIMEOUTS_MS.deepLinkResolution
    );

    const decision = resolveInitialRoute({
      environmentValid: Boolean(environmentValid),
      buildSupported: true,
      config: effectiveConfig,
      configSource,
      currentVersion: environment.buildVersion,
      currentBuildNumber: environment.buildNumber,
      platform: input.platform,
      connectivity: effectiveConnectivity,
      auth,
      onboarding,
      pendingDeepLink: consumePendingDestination(),
      startupFailed: false,
    });

    await runPhase(sequenceId, "resolving-initial-route", async () => decision);
    if (sequenceId !== activeSequenceId) return snapshot;
    dispatch({ type: "ROUTE_RESOLVED", decision });

    if (decision.degradedMode) {
      dispatch({ type: "DEGRADED", at: new Date().toISOString() });
    } else {
      dispatch({ type: "READY", at: new Date().toISOString() });
    }

    logger.info("startup.completed", { route: decision.routeId, reason: decision.reason, source: configSource });
    return snapshot;
  } catch (err) {
    if (sequenceId !== activeSequenceId) return snapshot;
    const startupError = err instanceof StartupError ? err : new StartupError("unknown", err instanceof Error ? err.message : "Unknown startup failure");
    dispatch({
      type: "FAILED",
      at: new Date().toISOString(),
      category: startupError.category,
      message: startupError.message,
      errorReferenceId: startupError.errorReferenceId,
    });
    logger.error("startup.failed", startupError, { errorReferenceId: startupError.errorReferenceId });
    return snapshot;
  } finally {
    if (sequenceId === activeSequenceId) running = false;
  }
}

function waitForTerminalSnapshot(): Promise<StartupSnapshot> {
  return new Promise((resolve) => {
    const unsubscribe = subscribeStartup((next) => {
      if (next.status === "ready" || next.status === "degraded" || next.status === "failed") {
        unsubscribe();
        resolve(next);
      }
    });
  });
}

/** Explicit retry — cancels any prior in-flight run via the sequence-id guard, then starts a fresh one. */
export async function retryStartup(input: StartupRunInput): Promise<StartupSnapshot> {
  running = false;
  return runStartup(input);
}

/**
 * Re-runs startup reusing the last known connectivity/platform — used by
 * the auth feature after login/logout so a session change is reflected in
 * the resolved route without every caller needing to know startup's input
 * shape. No-ops if startup has never run yet (nothing to react to).
 */
export async function reevaluateStartup(): Promise<StartupSnapshot | undefined> {
  if (!lastRunInput) return undefined;
  return retryStartup(lastRunInput);
}

/** Test-only reset. */
export function __resetStartupServiceForTests(): void {
  snapshot = createInitialStartupSnapshot();
  activeSequenceId = 0;
  running = false;
  listeners.clear();
}
