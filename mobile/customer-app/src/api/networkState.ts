import NetInfo, { NetInfoState } from "@react-native-community/netinfo";

/**
 * Network awareness. Publishes a small, UI-safe NetworkState -- consumers
 * read this instead of importing NetInfo directly, so "connectivity" stays
 * decoupled from "backend health" (a device can be `online` here and still
 * fail an API call for other reasons).
 */
export type NetworkState = "online" | "offline" | "internet_reachable_false" | "unknown";

type Listener = (state: NetworkState) => void;

let current: NetworkState = "unknown";
let previous: NetworkState = "unknown";
const listeners = new Set<Listener>();
let unsubscribeNetInfo: (() => void) | null = null;
const reconnectHandlers = new Set<() => void>();

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
