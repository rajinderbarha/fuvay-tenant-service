import { createNavigationContainerRef, CommonActions } from "@react-navigation/native";
import { isKnownRouteId } from "./route-registry";
import { logger } from "../observability/logger";
import type { RootStackParamList } from "./route-types";

/**
 * Navigation entry point for non-component contexts only (e.g. a push
 * notification handler, an API-client 401 handler). Screens should use
 * `useNavigation()` directly rather than this service. The ref itself is
 * intentionally not exported — every other module goes through the
 * functions below so navigation stays centrally validated and logged.
 */
const navigationRef = createNavigationContainerRef<RootStackParamList>();

let queuedIntent: { name: keyof RootStackParamList; params: unknown } | null = null;
let lastNavigation: { name: string; at: number } | null = null;
const DUPLICATE_NAVIGATION_WINDOW_MS = 400;

export function isNavigationReady(): boolean {
  return navigationRef.isReady();
}

function isDuplicateNavigation(name: string): boolean {
  if (!lastNavigation) return false;
  return lastNavigation.name === name && Date.now() - lastNavigation.at < DUPLICATE_NAVIGATION_WINDOW_MS;
}

function recordNavigation(name: string) {
  lastNavigation = { name, at: Date.now() };
  logger.debug("navigation.navigate", { route: name });
}

/**
 * Navigates immediately if the container is ready; otherwise queues exactly
 * one pending intent to be flushed by `flushQueuedIntent()` once the
 * container mounts. A second call before the container is ready replaces
 * the queued intent rather than stacking multiple.
 */
export function navigate<RouteName extends keyof RootStackParamList>(
  name: RouteName,
  ...args: RootStackParamList[RouteName] extends undefined ? [] : [RootStackParamList[RouteName]]
): boolean {
  if (!isKnownRouteId(name as string)) {
    logger.warn("navigation.rejected_unknown_route", { route: String(name) });
    return false;
  }

  const params = args[0];

  if (!navigationRef.isReady()) {
    queuedIntent = { name, params };
    return false;
  }

  if (isDuplicateNavigation(name as string)) return false;

  // @ts-expect-error — React Navigation's overload set doesn't tuple-spread cleanly through a generic wrapper.
  navigationRef.navigate(name, params);
  recordNavigation(name as string);
  return true;
}

export function replace<RouteName extends keyof RootStackParamList>(
  name: RouteName,
  ...args: RootStackParamList[RouteName] extends undefined ? [] : [RootStackParamList[RouteName]]
): boolean {
  if (!navigationRef.isReady() || !isKnownRouteId(name as string)) return false;
  const params = args[0];
  navigationRef.dispatch(CommonActions.reset({ index: 0, routes: [{ name: name as string, params: params as object | undefined }] }));
  recordNavigation(name as string);
  return true;
}

export function resetTo(name: keyof RootStackParamList): boolean {
  if (!navigationRef.isReady() || !isKnownRouteId(name as string)) return false;
  navigationRef.dispatch(CommonActions.reset({ index: 0, routes: [{ name: name as string }] }));
  recordNavigation(name as string);
  return true;
}

export function goBackIfSafe(): boolean {
  if (!navigationRef.isReady()) return false;
  if (!navigationRef.canGoBack()) return false;
  navigationRef.goBack();
  return true;
}

export function getCurrentRouteName(): string | undefined {
  if (!navigationRef.isReady()) return undefined;
  return navigationRef.getCurrentRoute()?.name;
}

/** Called once by the root navigator's `onReady` callback. */
export function flushQueuedIntent(): void {
  if (!queuedIntent || !navigationRef.isReady()) return;
  const intent = queuedIntent;
  queuedIntent = null;
  // @ts-expect-error — see navigate() above.
  navigationRef.navigate(intent.name, intent.params);
  recordNavigation(intent.name as string);
}

export function getNavigationRefForContainer(): typeof navigationRef {
  return navigationRef;
}
