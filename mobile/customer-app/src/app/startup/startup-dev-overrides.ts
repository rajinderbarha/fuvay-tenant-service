/**
 * Development-only startup simulations. Every read of these overrides is
 * guarded by `__DEV__` at the call site in startup-service.ts, and this
 * module itself is only imported from the dev-gated StartupInspectorScreen —
 * there is no code path that can activate a simulation in a production
 * bundle, since `__DEV__` is a compile-time constant Metro strips in release
 * builds.
 */
export interface StartupDevOverrides {
  forceOffline: boolean;
  forceMandatoryUpdate: boolean;
  forceMaintenance: boolean;
  forceInvalidDeepLink: boolean;
}

let overrides: StartupDevOverrides = {
  forceOffline: false,
  forceMandatoryUpdate: false,
  forceMaintenance: false,
  forceInvalidDeepLink: false,
};

export function getStartupDevOverrides(): StartupDevOverrides {
  return overrides;
}

export function setStartupDevOverride<K extends keyof StartupDevOverrides>(key: K, value: StartupDevOverrides[K]): void {
  if (!__DEV__) return;
  overrides = { ...overrides, [key]: value };
}

export function resetStartupDevOverrides(): void {
  overrides = { forceOffline: false, forceMandatoryUpdate: false, forceMaintenance: false, forceInvalidDeepLink: false };
}
