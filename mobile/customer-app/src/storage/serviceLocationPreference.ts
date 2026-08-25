import { getLocalItem, removeLocalItem, setLocalItem } from "./localStorage";

const STORAGE_KEY = "customer_app_service_location_v1";

/**
 * A service-location PIN is a non-sensitive browsing preference. It is
 * deliberately separate from saved addresses: choosing an area on Home must
 * not silently create or mutate an address, but the choice still needs to be
 * available to the Assistant and survive tab switches/app restarts.
 */
export function normalizeServiceZipcode(value: string | null | undefined): string | null {
  const normalized = value?.trim() ?? "";
  if (!normalized || normalized.length > 12) return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9 -]*$/.test(normalized)) return null;
  return normalized;
}

export async function loadServiceLocationPreference(): Promise<string | null> {
  const stored = await getLocalItem(STORAGE_KEY);
  return normalizeServiceZipcode(stored);
}

export async function saveServiceLocationPreference(zipcode: string): Promise<string> {
  const normalized = normalizeServiceZipcode(zipcode);
  if (!normalized) throw new Error("Invalid service location");
  await setLocalItem(STORAGE_KEY, normalized);
  return normalized;
}

export async function clearServiceLocationPreference(): Promise<void> {
  await removeLocalItem(STORAGE_KEY);
}

