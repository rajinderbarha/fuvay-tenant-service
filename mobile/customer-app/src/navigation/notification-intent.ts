import { ROUTE_REGISTRY, type RouteId } from "./route-registry";

/**
 * Push registration and the notification inbox are not implemented this
 * sprint — only the normalized contract a future notification handler must
 * produce, plus the validation that keeps a raw payload from navigating
 * anywhere it likes.
 */
export interface NotificationNavigationIntent {
  notificationId: string;
  type: string;
  route: string;
  params: unknown;
  receivedAt: string;
  expiresAt?: string;
}

export type NotificationIntentRejectionReason = "route_not_allowlisted" | "expired" | "malformed_params" | "duplicate";

export type NotificationIntentResult =
  { ok: true; routeId: RouteId; params: Record<string, string> } | { ok: false; reason: NotificationIntentRejectionReason };

const consumedNotificationIds = new Set<string>();

/**
 * Never trusts `intent.route` as a literal navigable route — it is only
 * accepted if it matches a route in the compiled registry AND that route is
 * explicitly `notificationEnabled`.
 */
export function resolveNotificationIntent(intent: NotificationNavigationIntent, nowIso: string = new Date().toISOString()): NotificationIntentResult {
  if (consumedNotificationIds.has(intent.notificationId)) {
    return { ok: false, reason: "duplicate" };
  }

  if (intent.expiresAt && new Date(intent.expiresAt).getTime() <= new Date(nowIso).getTime()) {
    return { ok: false, reason: "expired" };
  }

  const definition = (ROUTE_REGISTRY as Record<string, (typeof ROUTE_REGISTRY)[RouteId]>)[intent.route];
  if (!definition || !definition.notificationEnabled) {
    return { ok: false, reason: "route_not_allowlisted" };
  }

  if (intent.params !== undefined && (typeof intent.params !== "object" || intent.params === null || Array.isArray(intent.params))) {
    return { ok: false, reason: "malformed_params" };
  }

  const rawParams = (intent.params ?? {}) as Record<string, unknown>;
  const params: Record<string, string> = {};
  for (const [key, value] of Object.entries(rawParams)) {
    if (typeof value !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(value)) {
      return { ok: false, reason: "malformed_params" };
    }
    params[key] = value;
  }

  consumedNotificationIds.add(intent.notificationId);
  return { ok: true, routeId: definition.id, params };
}

export function __resetNotificationIntentDedupeForTests(): void {
  consumedNotificationIds.clear();
}
