import NetInfo, { NetInfoState } from "@react-native-community/netinfo";
import { NetworkState } from "./types";

/**
 * Network awareness (Phase F spec section 15). Publishes a small, UI-safe
 * NetworkState -- consumers (retry policy, restricted-state UI, reconnect
 * revalidation) read this instead of importing NetInfo directly, so
 * "connectivity" stays decoupled from "backend health" (a device can be
 * `online` here and still get NETWORK_TIMEOUT/SERVER_UNAVAILABLE from the
 * API layer).
 */
type Listener = (state: NetworkState) => void;

let current: NetworkState = "unknown";
let previous: NetworkState = "unknown";
const listeners = new Set<Listener>();
let unsubscribeNetInfo: (() => void) | null = null;
let reconnectHandlers = new Set<() => void>();

function classify(state: NetInfoState): NetworkState {
  if (state.isConnected === false) return "offline";
  if (state.isInternetReachable === false) return "internet_reachable_false";
  if (state.isConnected === true) return "online";
  return "unknown";
}

function setState(next: NetworkState) {
  if (next === current) return;
  previous = current;
  current = next;
  // Reconnect = we were offline/unreachable and are now online. Guarded so
  // a flappy connection can't fire multiple overlapping reconnect refreshes
  // in a row; callers (sessionManager) additionally dedupe via their own
  // in-flight guard, this is just the network-layer half.
  const isReconnect = next === "online" && (previous === "offline" || previous === "internet_reachable_false");
  listeners.forEach(l => l(current));
  if (isReconnect) reconnectHandlers.forEach(h => h());
}

export function startNetworkMonitoring(): void {
  if (unsubscribeNetInfo) return;
  unsubscribeNetInfo = NetInfo.addEventListener(state => setState(classify(state)));
  NetInfo.fetch().then(state => setState(classify(state))).catch(() => setState("unknown"));
}

export function stopNetworkMonitoring(): void {
  unsubscribeNetInfo?.();
  unsubscribeNetInfo = null;
}

export function getNetworkState(): NetworkState {
  return current;
}

export function isOffline(): boolean {
  return current === "offline" || current === "internet_reachable_false";
}

export function subscribeNetworkState(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Fires (at most once per online transition) when connectivity is
 * restored after being offline/unreachable -- used to trigger one
 * controlled session/context revalidation, never an unsafe mutation replay. */
export function onReconnect(handler: () => void): () => void {
  reconnectHandlers.add(handler);
  return () => reconnectHandlers.delete(handler);
}

/** Test-only reset. */
export function __resetNetworkStateForTests(): void {
  current = "unknown";
  previous = "unknown";
  listeners.clear();
  reconnectHandlers.clear();
}
