import { evaluateCacheUsability } from "../remote-config-cache";
import type { ConfigCacheEntry } from "../remote-config-types";

function entry(overrides: Partial<ConfigCacheEntry> = {}): ConfigCacheEntry {
  return {
    payload: {} as ConfigCacheEntry["payload"],
    schemaVersion: 1,
    configVersion: "v1",
    fetchedAt: "2026-06-01T00:00:00.000Z",
    environment: "development",
    marketplaceId: "default",
    validationStatus: "valid",
    integrityStatus: "unverified",
    appVersionFetched: "1.0.0",
    ...overrides,
  };
}

describe("evaluateCacheUsability", () => {
  const opts = { nowIso: "2026-06-01T00:05:00.000Z", environment: "development", marketplaceId: "default", maxAgeSeconds: 3600, allowStale: false };

  it("is usable and fresh for a recent, matching entry", () => {
    const result = evaluateCacheUsability(entry(), opts);
    expect(result.usable).toBe(true);
    expect(result.fresh).toBe(true);
  });

  it("rejects a cache entry from a different environment", () => {
    const result = evaluateCacheUsability(entry({ environment: "production" }), opts);
    expect(result.usable).toBe(false);
    expect(result.reason).toBe("environment_mismatch");
  });

  it("rejects a cache entry for a different marketplace", () => {
    const result = evaluateCacheUsability(entry({ marketplaceId: "other" }), opts);
    expect(result.usable).toBe(false);
    expect(result.reason).toBe("marketplace_mismatch");
  });

  it("is unusable when older than maxAgeSeconds and stale is not permitted", () => {
    const result = evaluateCacheUsability(entry(), { ...opts, nowIso: "2026-06-01T02:00:00.000Z", allowStale: false });
    expect(result.usable).toBe(false);
    expect(result.reason).toBe("too_old");
  });

  it("is usable-but-stale when older than maxAgeSeconds and stale IS permitted, within age", () => {
    const result = evaluateCacheUsability(entry(), { ...opts, nowIso: "2026-06-01T00:50:00.000Z", maxAgeSeconds: 7200, allowStale: true });
    expect(result.usable).toBe(true);
  });

  it("treats an explicit expiresAt as authoritative even before maxAgeSeconds elapses", () => {
    const result = evaluateCacheUsability(entry({ expiresAt: "2026-06-01T00:01:00.000Z" }), { ...opts, allowStale: false });
    expect(result.usable).toBe(false);
    expect(result.reason).toBe("expired");
  });

  it("allows an expired-but-within-maxAge entry when stale is permitted", () => {
    const result = evaluateCacheUsability(entry({ expiresAt: "2026-06-01T00:01:00.000Z" }), { ...opts, allowStale: true });
    expect(result.usable).toBe(true);
    expect(result.fresh).toBe(false);
  });
});
