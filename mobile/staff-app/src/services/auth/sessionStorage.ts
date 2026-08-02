import * as SecureStore from "expo-secure-store";
import { StoredSessionBundle } from "./types";

/**
 * SecureStore-backed session storage (Phase F spec section 5). Namespaced
 * and versioned so a future schema change can migrate/clear safely without
 * guessing at old key names. Never stores password/OTP/MFA code, never
 * stores the full /me or job/customer records -- only the sensitive
 * session material itself.
 */
const NAMESPACE = "serviceos.staffapp.session";
const CURRENT_SCHEMA_VERSION = 1;
const BUNDLE_KEY = `${NAMESPACE}.v${CURRENT_SCHEMA_VERSION}.bundle`;

// Keys from a prior schema version, if any is ever introduced, get listed
// here so `clearObsoleteKeys` can remove them without a full reinstall.
const OBSOLETE_KEYS: string[] = [];

export async function readSessionBundle(): Promise<StoredSessionBundle | null> {
  let raw: string | null;
  try {
    raw = await SecureStore.getItemAsync(BUNDLE_KEY);
  } catch {
    // SecureStore unavailable (e.g. simulator keychain issue) -- treat as
    // "nothing stored" rather than crash; the caller resolves unauthenticated.
    return null;
  }
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // Corrupt value -- never return a partially-restored session.
    await clearSessionBundle();
    return null;
  }

  if (!isValidBundle(parsed)) {
    await clearSessionBundle();
    return null;
  }
  return parsed;
}

function isValidBundle(value: unknown): value is StoredSessionBundle {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.schemaVersion === CURRENT_SCHEMA_VERSION &&
    typeof v.accessToken === "string" && v.accessToken.length > 0 &&
    typeof v.refreshToken === "string" && v.refreshToken.length > 0
  );
}

/** Persists a rotated/established bundle atomically from the caller's
 * point of view: either this resolves and the new bundle is fully written,
 * or it throws and the caller must treat persistence as failed (spec
 * section 9: "If persistence fails after rotation, fail closed"). */
export async function writeSessionBundle(bundle: StoredSessionBundle): Promise<void> {
  await SecureStore.setItemAsync(BUNDLE_KEY, JSON.stringify(bundle));
}

export async function clearSessionBundle(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(BUNDLE_KEY);
  } catch {
    // Best-effort -- caller still proceeds to clear in-memory state either way.
  }
}

export async function clearObsoleteKeys(): Promise<void> {
  await Promise.all(OBSOLETE_KEYS.map(key => SecureStore.deleteItemAsync(key).catch(() => {})));
}
