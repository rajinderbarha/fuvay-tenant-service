import * as SecureStore from "expo-secure-store";

/**
 * Secure storage for sensitive session material only: access tokens,
 * refresh tokens, trusted-device/session identifiers. Never store
 * preferences or drafts here (use src/storage/localStorage.ts) -- this
 * abstraction exists precisely so screens can never accidentally reach
 * for the wrong one, and so the real auth implementation (a later phase)
 * has a ready, tested place to write to.
 */
export async function setSecureItem(key: string, value: string): Promise<void> {
  await SecureStore.setItemAsync(key, value);
}

export async function getSecureItem(key: string): Promise<string | null> {
  return SecureStore.getItemAsync(key);
}

export async function deleteSecureItem(key: string): Promise<void> {
  await SecureStore.deleteItemAsync(key);
}

export const SecureStorageKeys = {
  accessToken: "customer_app_access_token",
  refreshToken: "customer_app_refresh_token",
  trustedDeviceId: "customer_app_trusted_device_id",
  /** Phase F token vault -- one atomic JSON record (see
   * api/session/tokenVault.ts) rather than the old Staff App pattern of
   * several independently-writable keys, which can partially fail and
   * leave a falsely-authenticated-looking state. */
  sessionRecord: "customer_app_session_record_v1",
} as const;
