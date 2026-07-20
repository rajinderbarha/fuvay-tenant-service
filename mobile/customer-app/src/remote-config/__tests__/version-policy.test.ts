import { compareVersions, isValidVersion, evaluateVersionPolicy } from "../version-policy";
import type { VersionPolicyConfig } from "../remote-config-schema";

const basePolicy: VersionPolicyConfig = {
  minSupportedVersion: "1.0.0",
  latestRecommendedVersion: "1.5.0",
  mandatoryUpdate: false,
  optionalUpdate: true,
  updateTitle: "Update",
  updateMessage: "Please update",
  gracePeriodHours: 0,
  blockedBuildNumbers: [],
};

describe("compareVersions", () => {
  it("orders 1.10.0 as newer than 1.9.9", () => {
    expect(compareVersions("1.10.0", "1.9.9")).toBe(1);
  });

  it("orders 2.0.0 as newer than 1.99.99", () => {
    expect(compareVersions("2.0.0", "1.99.99")).toBe(1);
  });

  it("treats equal versions as equal", () => {
    expect(compareVersions("1.2.3", "1.2.3")).toBe(0);
  });

  it("treats a release as newer than the same core prerelease", () => {
    expect(compareVersions("1.2.3", "1.2.3-beta.1")).toBe(1);
  });

  it("throws on an invalid version string", () => {
    expect(() => compareVersions("not-a-version", "1.0.0")).toThrow();
  });
});

describe("isValidVersion", () => {
  it.each(["1.0.0", "0.0.1", "10.20.30", "1.0.0-beta.1"])("accepts %s", (v) => expect(isValidVersion(v)).toBe(true));
  it.each(["1.0", "abc", "1.0.0.0", ""])("rejects %s", (v) => expect(isValidVersion(v)).toBe(false));
});

describe("evaluateVersionPolicy", () => {
  it("reports supported-current for an up-to-date version", () => {
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "1", platform: "android", policy: basePolicy }).outcome).toBe(
      "supported-current"
    );
  });

  it("reports supported-update-available when behind latest but optionalUpdate is false", () => {
    const policy = { ...basePolicy, optionalUpdate: false };
    expect(evaluateVersionPolicy({ currentVersion: "1.2.0", currentBuildNumber: "1", platform: "android", policy }).outcome).toBe("supported-update-available");
  });

  it("reports supported-update-recommended when behind latest and optionalUpdate is true", () => {
    expect(evaluateVersionPolicy({ currentVersion: "1.2.0", currentBuildNumber: "1", platform: "android", policy: basePolicy }).outcome).toBe(
      "supported-update-recommended"
    );
  });

  it("reports mandatory-update when below the minimum supported version", () => {
    expect(evaluateVersionPolicy({ currentVersion: "0.9.0", currentBuildNumber: "1", platform: "android", policy: basePolicy }).outcome).toBe(
      "mandatory-update"
    );
  });

  it("reports mandatory-update when the policy itself sets mandatoryUpdate", () => {
    const policy = { ...basePolicy, mandatoryUpdate: true };
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "1", platform: "android", policy }).outcome).toBe("mandatory-update");
  });

  it("reports blocked-build for a build in the blocklist regardless of version", () => {
    const policy = { ...basePolicy, blockedBuildNumbers: ["42"] };
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "42", platform: "android", policy }).outcome).toBe("blocked-build");
  });

  it("reports grace-period when below minimum but still inside the grace window", () => {
    const policy = { ...basePolicy, minSupportedVersion: "1.5.0", gracePeriodHours: 48 };
    const belowMinimumSinceIso = "2026-01-01T00:00:00.000Z";
    const nowIso = "2026-01-02T00:00:00.000Z"; // 24h later, within 48h grace
    expect(evaluateVersionPolicy({ currentVersion: "1.2.0", currentBuildNumber: "1", platform: "android", policy, belowMinimumSinceIso, nowIso }).outcome).toBe(
      "grace-period"
    );
  });

  it("reports mandatory-update once the grace period has elapsed", () => {
    const policy = { ...basePolicy, minSupportedVersion: "1.5.0", gracePeriodHours: 24 };
    const belowMinimumSinceIso = "2026-01-01T00:00:00.000Z";
    const nowIso = "2026-01-03T00:00:00.000Z"; // 48h later, past 24h grace
    expect(evaluateVersionPolicy({ currentVersion: "1.2.0", currentBuildNumber: "1", platform: "android", policy, belowMinimumSinceIso, nowIso }).outcome).toBe(
      "mandatory-update"
    );
  });

  it("reports invalid-policy for a malformed policy version", () => {
    const policy = { ...basePolicy, minSupportedVersion: "not-a-version" };
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "1", platform: "android", policy }).outcome).toBe("invalid-policy");
  });

  it("selects the platform-specific store URL", () => {
    const policy = {
      ...basePolicy,
      mandatoryUpdate: true,
      storeUrlIOS: "https://apps.apple.com/app/x",
      storeUrlAndroid: "https://play.google.com/store/apps/details?id=x",
    };
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "1", platform: "ios", policy }).storeUrl).toBe(policy.storeUrlIOS);
    expect(evaluateVersionPolicy({ currentVersion: "1.5.0", currentBuildNumber: "1", platform: "android", policy }).storeUrl).toBe(policy.storeUrlAndroid);
  });
});
