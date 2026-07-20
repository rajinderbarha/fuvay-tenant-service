import type { RouteId } from "../route-registry";
import type { DeepLinkSource } from "../route-params";

export interface PendingDestination {
  routeId: RouteId;
  params: Record<string, string>;
  source: DeepLinkSource;
  receivedAt: string;
  expiresAt: string;
  requiresAuth: boolean;
  requiresMarketplace: boolean;
  consumed: boolean;
}

/** Deep links carry no secrets and route ids/params are small, but this is
 * still kept memory-only (never written to disk) — the OS redelivers the
 * initial URL if the app is relaunched via the same link, so persistence
 * would only add replay risk with no real recovery benefit. */
const DEFAULT_TTL_MS = 5 * 60 * 1000;

let current: PendingDestination | null = null;

export function setPendingDestination(
  input: Omit<PendingDestination, "receivedAt" | "expiresAt" | "consumed">,
  nowIso: string = new Date().toISOString()
): void {
  current = {
    ...input,
    receivedAt: nowIso,
    expiresAt: new Date(new Date(nowIso).getTime() + DEFAULT_TTL_MS).toISOString(),
    consumed: false,
  };
}

/** Consume-once: returns the pending destination exactly once, then clears it. Prevents replay. */
export function consumePendingDestination(nowIso: string = new Date().toISOString()): PendingDestination | null {
  if (!current || current.consumed) return null;
  if (new Date(current.expiresAt).getTime() <= new Date(nowIso).getTime()) {
    current = null;
    return null;
  }
  const destination = current;
  current = { ...current, consumed: true };
  return destination;
}

export function peekPendingDestination(): PendingDestination | null {
  return current && !current.consumed ? current : null;
}

export function clearPendingDestination(): void {
  current = null;
}
