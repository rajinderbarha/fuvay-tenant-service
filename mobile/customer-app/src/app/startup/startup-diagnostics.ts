import { environment } from "../../config/environment";
import { peekPendingDestination } from "../../navigation/deep-links/pending-deep-link-store";
import type { StartupSnapshot } from "./startup-types";

export interface StartupDiagnostics {
  environment: string;
  appVersion: string;
  buildNumber: string;
  status: StartupSnapshot["status"];
  currentPhase: string;
  phaseDurationsMs: { phase: string; durationMs: number | null; result?: string }[];
  configVersion?: string;
  configSource?: string;
  connectivity: string;
  routeReason?: string;
  pendingDeepLinkRouteId?: string;
}

/**
 * Dev-only. Never includes tokens, addresses, notification payloads, or a
 * full config dump — only the safe fields a developer needs to debug a
 * startup decision.
 */
export function buildStartupDiagnostics(snapshot: StartupSnapshot): StartupDiagnostics {
  const pending = peekPendingDestination();

  return {
    environment: environment.name,
    appVersion: environment.buildVersion,
    buildNumber: environment.buildNumber,
    status: snapshot.status,
    currentPhase: snapshot.currentPhase,
    phaseDurationsMs: snapshot.phaseHistory.map((record) => ({
      phase: record.phase,
      durationMs: record.completedAt ? new Date(record.completedAt).getTime() - new Date(record.startedAt).getTime() : null,
      result: record.result,
    })),
    configVersion: snapshot.resolvedConfig?.config.configVersion,
    configSource: snapshot.resolvedConfig?.source,
    connectivity: snapshot.connectivity,
    routeReason: snapshot.routeDecision?.reason,
    pendingDeepLinkRouteId: pending?.routeId,
  };
}
