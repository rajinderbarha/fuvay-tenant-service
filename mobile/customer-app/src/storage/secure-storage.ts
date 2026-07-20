import * as SecureStore from "expo-secure-store";
import type { SecureStorageKey } from "./storage-keys";

/**
 * Adapter over the platform keychain (iOS Keychain / Android Keystore via
 * expo-secure-store). Use only for security-sensitive values: auth tokens,
 * device binding identifiers. Never write secrets here via console/log calls.
 */
export const secureStorage = {
  async getItem(key: SecureStorageKey): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      // Keychain access can fail (e.g. device locked, simulator quirks) —
      // fail closed by treating it as "not present" rather than throwing
      // into screen code.
      return null;
    }
  },

  async setItem(key: SecureStorageKey, value: string): Promise<boolean> {
    try {
      await SecureStore.setItemAsync(key, value);
      return true;
    } catch {
      return false;
    }
  },

  async removeItem(key: SecureStorageKey): Promise<boolean> {
    try {
      await SecureStore.deleteItemAsync(key);
      return true;
    } catch {
      return false;
    }
  },
};
