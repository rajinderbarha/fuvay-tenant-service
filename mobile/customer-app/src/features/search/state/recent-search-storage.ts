import AsyncStorage from "@react-native-async-storage/async-storage";

const MAX_RECENT_SEARCHES = 10;
const KEY_PREFIX = "serviceos.pref.recentSearches.v1";

/**
 * There is no backend recent-search or search-history endpoint at all
 * (CUSTOMER-L5-04-contract-matrix.md) — this is genuinely local-only
 * storage, never a fake substitute for a real one. Keyed by `customerId` so
 * one device can never leak a previous customer's search history to the
 * next signed-in customer on the same device (CUSTOMER-L5-04 §22/§63).
 * Uses plain (non-secure) storage deliberately — search terms are not
 * credentials, matching `preference-storage.ts`'s "non-sensitive" scope,
 * though this module manages its own dynamic per-customer keys rather than
 * the app's static `PreferenceStorageKey` enum.
 */
function storageKey(customerId: string): string {
  return `${KEY_PREFIX}:${customerId}`;
}

export async function getRecentSearches(customerId: string): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(storageKey(customerId));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

/** Moves an existing entry to the front rather than duplicating it; caps the list at MAX_RECENT_SEARCHES. */
export async function addRecentSearch(customerId: string, query: string): Promise<string[]> {
  const existing = await getRecentSearches(customerId);
  const deduped = [query, ...existing.filter((item) => item.toLowerCase() !== query.toLowerCase())].slice(0, MAX_RECENT_SEARCHES);
  try {
    await AsyncStorage.setItem(storageKey(customerId), JSON.stringify(deduped));
  } catch {
    // Best-effort — a failed write must not block the search itself.
  }
  return deduped;
}

export async function removeRecentSearch(customerId: string, query: string): Promise<string[]> {
  const existing = await getRecentSearches(customerId);
  const filtered = existing.filter((item) => item !== query);
  try {
    await AsyncStorage.setItem(storageKey(customerId), JSON.stringify(filtered));
  } catch {
    // Best-effort.
  }
  return filtered;
}

/** Called on logout/logout-all so no customer's search history survives an account switch on a shared device. */
export async function clearRecentSearches(customerId: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(storageKey(customerId));
  } catch {
    // Best-effort.
  }
}
