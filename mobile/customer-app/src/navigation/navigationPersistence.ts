/**
 * Navigation persistence policy (spec section 17). Deliberately narrow:
 * only the last selected global tab and one validated pending deep link
 * are ever written. Never raw React Navigation state (which could embed
 * arbitrary route params -- customer payloads, tokens, addresses).
 */
import { getLocalJSON, setLocalJSON, removeLocalItem } from "../storage/localStorage";
import { PendingDeepLink } from "./guards/types";
import { CustomerTabName } from "./routeTypes";

export const NAVIGATION_PERSISTENCE_SCHEMA_VERSION = 1;

interface PersistedNavigationState {
  schemaVersion: typeof NAVIGATION_PERSISTENCE_SCHEMA_VERSION;
  lastSelectedTab?: CustomerTabName;
  pendingDeepLink?: PendingDeepLink;
}

const STORAGE_KEY = "customer_app_navigation_state_v1";

export async function loadPersistedNavigationState(): Promise<PersistedNavigationState | null> {
  const stored = await getLocalJSON<PersistedNavigationState>(STORAGE_KEY);
  if (!stored) return null;
  if (stored.schemaVersion !== NAVIGATION_PERSISTENCE_SCHEMA_VERSION) {
    // Safe-discard rather than risk misinterpreting an incompatible shape
    // from an older app build.
    await removeLocalItem(STORAGE_KEY);
    return null;
  }
  // A pending deep link that failed validation must never be resurrected
  // on the next launch -- only a validated one is worth persisting at all.
  if (stored.pendingDeepLink && !stored.pendingDeepLink.validated) {
    return { ...stored, pendingDeepLink: undefined };
  }
  return stored;
}

export async function saveLastSelectedTab(tab: CustomerTabName): Promise<void> {
  const existing = (await loadPersistedNavigationState()) ?? { schemaVersion: NAVIGATION_PERSISTENCE_SCHEMA_VERSION };
  await setLocalJSON(STORAGE_KEY, { ...existing, lastSelectedTab: tab });
}

export async function savePendingDeepLink(link: PendingDeepLink | undefined): Promise<void> {
  const existing = (await loadPersistedNavigationState()) ?? { schemaVersion: NAVIGATION_PERSISTENCE_SCHEMA_VERSION };
  await setLocalJSON(STORAGE_KEY, { ...existing, pendingDeepLink: link });
}

export async function clearPersistedNavigationState(): Promise<void> {
  await removeLocalItem(STORAGE_KEY);
}
