/**
 * Deliberate, per-operation timeouts (not one blanket value). All are
 * conservative enough for a slow connection but bounded so nothing spins
 * forever. Configuration-driven via a single object rather than scattered
 * magic numbers, per phase.
 */
export const STARTUP_TIMEOUTS_MS = {
  environmentValidation: 500,
  preferenceHydration: 2000,
  secureSessionPlaceholderRead: 2000,
  remoteConfigFetch: 8000,
  totalBlockingStartup: 12000,
  deepLinkResolution: 500,
  storeOpenAction: 5000,
} as const;

export type StartupTimeoutKey = keyof typeof STARTUP_TIMEOUTS_MS;

export function withTimeout<T>(promise: Promise<T>, ms: number, onTimeoutMessage: string): Promise<T> {
  let timeoutHandle: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timeoutHandle = setTimeout(() => reject(new Error(onTimeoutMessage)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutHandle)) as Promise<T>;
}
