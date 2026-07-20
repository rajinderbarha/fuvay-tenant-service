import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY_PREFIX = "serviceos.pref.activeDraftId.v1";

/**
 * Stores only a draft ID — never the draft content itself, never tokens,
 * never diagnostic answers (CUSTOMER-L5-06 §18's "safe recovery" scope).
 * The ID alone is not sensitive; the backend remains the sole source of
 * truth for everything the ID points to, re-fetched and re-validated
 * (ownership, expiry, status) on every restore (see draft-architecture.md).
 * Keyed by customerId so one device can never resume a different
 * customer's draft after an account switch on a shared device.
 */
function storageKey(customerId: string): string {
  return `${KEY_PREFIX}:${customerId}`;
}

export async function getActiveDraftId(customerId: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(storageKey(customerId));
  } catch {
    return null;
  }
}

export async function setActiveDraftId(customerId: string, draftId: string): Promise<void> {
  try {
    await AsyncStorage.setItem(storageKey(customerId), draftId);
  } catch {
    // Best-effort — a failed local write must not block the in-session draft flow.
  }
}

export async function clearActiveDraftId(customerId: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(storageKey(customerId));
  } catch {
    // Best-effort.
  }
}
