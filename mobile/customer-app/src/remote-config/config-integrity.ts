import { environment } from "../config/environment";
import { bindableEnvironmentName } from "./remote-config-types";
import type { RemoteConfigEnvelope } from "./remote-config-schema";

export type IntegrityStatus = "trusted" | "unverified" | "rejected";

export interface IntegrityCheckInput {
  envelope: RemoteConfigEnvelope;
  sourceUrl: string;
  marketplaceContextId: string;
}

export interface IntegrityCheckResult {
  status: IntegrityStatus;
  reason?: string;
}

const TRUSTED_HOSTS_BY_ENV: Record<string, string[]> = {
  production: ["api.serviceos.in"],
  staging: ["staging-api.serviceos.in"],
};

/**
 * Integrity-verification abstraction. This backend does not currently issue
 * signed configuration payloads, so this is intentionally NOT a
 * cryptographic signature check — see docs/customer-app/remote-configuration.md
 * for the honest gap statement. What this DOES verify:
 *   - the config was served from a trusted origin for the active environment
 *   - the config's declared environment matches the build's environment
 *   - the config's marketplace matches the context that requested it
 * A config that fails any of these is marked "rejected" and must not be used
 * even if it passed schema validation.
 */
export function verifyConfigIntegrity(input: IntegrityCheckInput): IntegrityCheckResult {
  const { envelope, sourceUrl, marketplaceContextId } = input;

  if (envelope.environment !== bindableEnvironmentName(environment.name)) {
    return { status: "rejected", reason: "environment_mismatch" };
  }

  if (envelope.marketplace.marketplaceId !== marketplaceContextId) {
    return { status: "rejected", reason: "marketplace_mismatch" };
  }

  const trustedHosts = TRUSTED_HOSTS_BY_ENV[environment.name];
  if (trustedHosts) {
    let host: string;
    try {
      host = new URL(sourceUrl).host;
    } catch {
      return { status: "rejected", reason: "invalid_source_url" };
    }
    if (!trustedHosts.includes(host)) {
      return { status: "rejected", reason: "untrusted_origin" };
    }
    // No cryptographic signature is available from the backend today —
    // origin + environment + marketplace binding is the full trust model.
    return { status: "unverified" };
  }

  // local/development: no fixed trusted-host list — origin trust comes from
  // the developer's own EXPO_PUBLIC_API_URL, which is out of this function's control.
  return { status: "unverified" };
}
