import { RouteKey, resolveRouteDefinition } from "./routeRegistry";

/**
 * Push-notification navigation contract (spec section 9). This defines the
 * shape and resolution logic only -- push token registration and the
 * actual notification-receiving wiring are out of scope for Phase E.
 * Payloads route through the exact same ROUTE_REGISTRY as deep links and
 * tab navigation; a push can never carry a raw URL or an ad hoc route.
 */
export const SUPPORTED_PUSH_SCHEMA_VERSION = 1;

export interface PushNotificationPayload {
  schemaVersion: number;
  notificationId: string;
  eventType: string;
  routeKey: string;
  entityId?: string;
  actionKey?: string;
}

export interface ResolvedPushRoute {
  routeKey: RouteKey;
  jobId?: string;
  targetAction?: string;
  notificationId: string;
}

export type PushRoutingFailure =
  | { ok: false; reason: "UNSUPPORTED_SCHEMA_VERSION" }
  | { ok: false; reason: "ROUTE_NOT_FOUND" }
  | { ok: false; reason: "DUPLICATE_NOTIFICATION" };

export type PushRoutingResult = { ok: true; route: ResolvedPushRoute } | PushRoutingFailure;

/** Tracks notificationIds already routed this session so a duplicate tap
 * (re-delivered push, double-tap, background+cold-start race) is a no-op
 * rather than a second navigation. */
const seenNotificationIds = new Set<string>();

export function resetSeenNotifications(): void {
  seenNotificationIds.clear();
}

export function resolvePushRoute(payload: PushNotificationPayload): PushRoutingResult {
  if (payload.schemaVersion !== SUPPORTED_PUSH_SCHEMA_VERSION) {
    return { ok: false, reason: "UNSUPPORTED_SCHEMA_VERSION" };
  }

  if (seenNotificationIds.has(payload.notificationId)) {
    return { ok: false, reason: "DUPLICATE_NOTIFICATION" };
  }

  const route = resolveRouteDefinition(payload.routeKey);
  if (!route) {
    return { ok: false, reason: "ROUTE_NOT_FOUND" };
  }

  if (route.requiresJobId && !payload.entityId) {
    return { ok: false, reason: "ROUTE_NOT_FOUND" };
  }

  seenNotificationIds.add(payload.notificationId);

  return {
    ok: true,
    route: {
      routeKey: route.key,
      jobId: route.requiresJobId ? payload.entityId : undefined,
      targetAction: payload.actionKey,
      notificationId: payload.notificationId,
    },
  };
}
