import type { VersionPolicyConfig } from "./remote-config-schema";

export type VersionPolicyOutcome =
  | "supported-current"
  | "supported-update-available"
  | "supported-update-recommended"
  | "grace-period"
  | "mandatory-update"
  | "blocked-build"
  | "unsupported-os"
  | "invalid-policy";

export interface VersionPolicyInput {
  currentVersion: string;
  currentBuildNumber: string;
  platform: "ios" | "android";
  policy: VersionPolicyConfig;
  /** ISO timestamp the app was first observed below the minimum version, if known — required to evaluate a grace period. */
  belowMinimumSinceIso?: string;
  nowIso?: string;
}

export interface VersionPolicyResult {
  outcome: VersionPolicyOutcome;
  storeUrl?: string;
}

/**
 * Parses a semantic version into comparable parts. Not a full semver
 * implementation (no build-metadata handling) — sufficient for the
 * comparisons this app's version policy actually needs.
 */
function parseVersion(version: string): { core: number[]; prerelease: string | null } | null {
  const match = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/.exec(version);
  if (!match) return null;
  return { core: [Number(match[1]), Number(match[2]), Number(match[3])], prerelease: match[4] ?? null };
}

/** Returns -1, 0, or 1. A release version is always newer than the same core version with a prerelease tag. */
export function compareVersions(a: string, b: string): number {
  const va = parseVersion(a);
  const vb = parseVersion(b);
  if (!va || !vb) throw new RangeError(`Invalid semantic version: "${!va ? a : b}"`);

  for (let i = 0; i < 3; i++) {
    if (va.core[i] !== vb.core[i]) return va.core[i] < vb.core[i] ? -1 : 1;
  }
  if (va.prerelease === vb.prerelease) return 0;
  if (va.prerelease === null) return 1;
  if (vb.prerelease === null) return -1;
  return va.prerelease < vb.prerelease ? -1 : va.prerelease > vb.prerelease ? 1 : 0;
}

export function isValidVersion(version: string): boolean {
  return parseVersion(version) !== null;
}

export function evaluateVersionPolicy(input: VersionPolicyInput): VersionPolicyResult {
  const { currentVersion, currentBuildNumber, policy } = input;

  if (!isValidVersion(currentVersion) || !isValidVersion(policy.minSupportedVersion) || !isValidVersion(policy.latestRecommendedVersion)) {
    return { outcome: "invalid-policy" };
  }

  if (policy.blockedBuildNumbers.includes(currentBuildNumber)) {
    return { outcome: "blocked-build" };
  }

  const storeUrl = input.platform === "ios" ? policy.storeUrlIOS : policy.storeUrlAndroid;

  if (policy.mandatoryUpdate || compareVersions(currentVersion, policy.minSupportedVersion) < 0) {
    if (policy.gracePeriodHours > 0 && input.belowMinimumSinceIso) {
      const now = input.nowIso ? new Date(input.nowIso) : new Date();
      const since = new Date(input.belowMinimumSinceIso);
      const hoursElapsed = (now.getTime() - since.getTime()) / (1000 * 60 * 60);
      if (hoursElapsed < policy.gracePeriodHours) {
        return { outcome: "grace-period", storeUrl };
      }
    }
    return { outcome: "mandatory-update", storeUrl };
  }

  const behindLatest = compareVersions(currentVersion, policy.latestRecommendedVersion) < 0;
  if (behindLatest && policy.optionalUpdate) {
    return { outcome: "supported-update-recommended", storeUrl };
  }
  if (behindLatest) {
    return { outcome: "supported-update-available", storeUrl };
  }

  return { outcome: "supported-current" };
}
