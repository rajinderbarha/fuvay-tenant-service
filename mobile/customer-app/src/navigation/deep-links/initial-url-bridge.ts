import * as Linking from "expo-linking";

/**
 * Captures the URL the app was launched with exactly once, so both the
 * startup orchestrator (which needs it during `resolving-deep-link`) and
 * React Navigation's `linking.getInitialURL` (which needs it for its own
 * bookkeeping) read the same value instead of racing two separate calls to
 * the native module.
 */
let cachedInitialUrl: string | null | undefined;

export async function getInitialUrlOnce(): Promise<string | null> {
  if (cachedInitialUrl !== undefined) return cachedInitialUrl;
  cachedInitialUrl = await Linking.getInitialURL();
  return cachedInitialUrl;
}

export function __resetInitialUrlBridgeForTests(): void {
  cachedInitialUrl = undefined;
}
