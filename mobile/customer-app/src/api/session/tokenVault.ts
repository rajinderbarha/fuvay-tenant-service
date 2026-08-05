import { setSecureItem, getSecureItem, deleteSecureItem, SecureStorageKeys } from "../../storage/secureStorage";
import { CustomerId } from "../../domain/ids";

/**
 * Customer-specific token vault (spec section 15). Refresh token lives
 * only in secure storage. The access token is kept in an in-memory module
 * variable for the common case (fast, never touches disk per-request),
 * but is ALSO persisted to the same secure record so a cold app start can
 * restore a still-valid session without forcing an immediate refresh --
 * both tokens are written together as one JSON blob under a single
 * SecureStore key, which is what makes the write atomic (there is no
 * multi-key partial-write state possible, unlike five separate keys).
 */
export const TOKEN_VAULT_SCHEMA_VERSION = 1;

export interface StoredSessionRecord {
  schemaVersion: typeof TOKEN_VAULT_SCHEMA_VERSION;
  accessToken: string;
  refreshToken: string | null;
  customerId: string;
  savedAt: string;
}

let inMemoryAccessToken: string | null = null;

export function getInMemoryAccessToken(): string | null {
  return inMemoryAccessToken;
}

function isWellFormedRecord(value: unknown): value is StoredSessionRecord {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.schemaVersion === TOKEN_VAULT_SCHEMA_VERSION &&
    typeof v.accessToken === "string" && v.accessToken.length > 0 &&
    (v.refreshToken === null || typeof v.refreshToken === "string") &&
    typeof v.customerId === "string" && v.customerId.length > 0 &&
    typeof v.savedAt === "string"
  );
}

/** Atomic save -- one JSON.stringify, one SecureStore write. Updates the
 * in-memory access token only after the secure write succeeds, so a
 * failed write can never leave memory and disk disagreeing about whether
 * a session exists. */
export async function saveSession(accessToken: string, refreshToken: string | null, customerId: CustomerId): Promise<void> {
  const record: StoredSessionRecord = {
    schemaVersion: TOKEN_VAULT_SCHEMA_VERSION,
    accessToken,
    refreshToken,
    customerId,
    savedAt: new Date().toISOString(),
  };
  await setSecureItem(SecureStorageKeys.sessionRecord, JSON.stringify(record));
  inMemoryAccessToken = accessToken;
}

/** Loads and validates the persisted record. A corrupted, partial or
 * version-mismatched record fails closed (returns null and clears
 * storage) rather than risk restoring a half-formed session -- spec
 * section 15 "partial writes cannot create a falsely authenticated
 * state" applies just as much to partially-CORRUPTED reads. */
export async function loadSession(): Promise<StoredSessionRecord | null> {
  let raw: string | null;
  try {
    raw = await getSecureItem(SecureStorageKeys.sessionRecord);
  } catch {
    // A SecureStore read failure (corrupted keychain entry, OS-level
    // access denial, or no SecureStore implementation on this platform)
    // must fail closed the same as "no session" -- previously this threw
    // uncaught up through restoreSession()'s bare `.catch(() => {})`,
    // which never transitions the session state machine out of
    // "restoring", permanently stranding the app on the boot splash
    // screen with no error and no recovery.
    return null;
  }
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    await clearSession();
    return null;
  }

  if (!isWellFormedRecord(parsed)) {
    await clearSession();
    return null;
  }

  inMemoryAccessToken = parsed.accessToken;
  return parsed;
}

export async function clearSession(): Promise<void> {
  inMemoryAccessToken = null;
  await deleteSecureItem(SecureStorageKeys.sessionRecord);
}

/** Updates only the token pair after a successful refresh, preserving
 * customerId -- rotation must remain atomic (one write), never two
 * separate access/refresh writes. */
export async function rotateTokens(accessToken: string, refreshToken: string, customerId: CustomerId): Promise<void> {
  await saveSession(accessToken, refreshToken, customerId);
}
