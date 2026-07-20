import { preferenceStorage } from "../storage/preference-storage";
import { PREFERENCE_STORAGE_KEYS } from "../storage/storage-keys";
import { remoteConfigEnvelopeSchema } from "./remote-config-schema";
import type { ConfigCacheEntry } from "./remote-config-types";

/**
 * Config never contains secrets (enforced by schema — no token/credential
 * fields exist), so non-sensitive preference storage is the correct adapter.
 */

export async function readConfigCache(): Promise<ConfigCacheEntry | null> {
  const raw = await preferenceStorage.getItem<ConfigCacheEntry>(PREFERENCE_STORAGE_KEYS.remoteConfigCache);
  if (!raw) return null;

  // Defend against a corrupted or partially-written cache entry — validate
  // the embedded payload against the schema again rather than trusting the
  // stored `validationStatus` flag blindly.
  const parsed = remoteConfigEnvelopeSchema.safeParse(raw.payload);
  if (!parsed.success) return null;

  return { ...raw, payload: parsed.data, validationStatus: "valid" };
}

export async function writeConfigCache(entry: ConfigCacheEntry): Promise<boolean> {
  return preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.remoteConfigCache, entry);
}

export async function clearConfigCache(): Promise<void> {
  await preferenceStorage.removeItem(PREFERENCE_STORAGE_KEYS.remoteConfigCache);
}

export interface CacheUsability {
  usable: boolean;
  fresh: boolean;
  reason?: "expired" | "environment_mismatch" | "marketplace_mismatch" | "too_old";
}

export function evaluateCacheUsability(
  entry: ConfigCacheEntry,
  opts: { nowIso: string; environment: string; marketplaceId: string; maxAgeSeconds: number; allowStale: boolean }
): CacheUsability {
  if (entry.environment !== opts.environment) return { usable: false, fresh: false, reason: "environment_mismatch" };
  if (entry.marketplaceId !== opts.marketplaceId) return { usable: false, fresh: false, reason: "marketplace_mismatch" };

  const now = new Date(opts.nowIso).getTime();
  const ageSeconds = (now - new Date(entry.fetchedAt).getTime()) / 1000;
  const expired = entry.expiresAt ? now >= new Date(entry.expiresAt).getTime() : false;

  if (expired) return { usable: opts.allowStale && ageSeconds <= opts.maxAgeSeconds, fresh: false, reason: "expired" };
  if (ageSeconds > opts.maxAgeSeconds) return { usable: opts.allowStale, fresh: false, reason: "too_old" };

  return { usable: true, fresh: true };
}
