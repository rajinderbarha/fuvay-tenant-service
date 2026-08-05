import { ENV } from "./environment";
import { logger } from "../utils/logger";

/**
 * Dev-only build/version fingerprint (physical-device verification, spec
 * "Verify the mobile build is current"). A stale Metro bundle or a phone
 * pointed at the wrong `EXPO_PUBLIC_API_BASE_URL` looks IDENTICAL to a
 * real backend defect from the screen alone -- this gives something
 * concrete to check first: the exact API base URL this bundle was built
 * against, and the timestamp this JS module was evaluated (changes on
 * every fresh Metro bundle/reload, never on a stale cached one). Logged
 * via the existing dev-only `logger` (a no-op in production) -- never
 * rendered in production UI, and never a secret (the API base URL is
 * already public per environment.ts's own contract).
 */
export const BUILD_FINGERPRINT = Object.freeze({
  apiBaseUrl: ENV.apiBaseUrl,
  appEnv: ENV.appEnv,
  bundleEvaluatedAt: new Date().toISOString(),
});

export function logBuildFingerprint(): void {
  if (!__DEV__) return;
  logger.info("build fingerprint", BUILD_FINGERPRINT);
}
