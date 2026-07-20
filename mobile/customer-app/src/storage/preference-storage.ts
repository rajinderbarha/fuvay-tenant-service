import AsyncStorage from "@react-native-async-storage/async-storage";
import { PREFERENCE_STORAGE_KEYS, type PreferenceStorageKey } from "./storage-keys";

/**
 * Adapter for non-sensitive persisted preferences only (theme, locale,
 * onboarding markers, dev toggles). Never store tokens or PII here.
 */
export const preferenceStorage = {
  async getItem<T>(key: PreferenceStorageKey): Promise<T | null> {
    try {
      const raw = await AsyncStorage.getItem(key);
      if (raw == null) return null;
      return JSON.parse(raw) as T;
    } catch {
      // Corrupted/unparseable value — recover by treating as unset rather
      // than crashing the caller.
      return null;
    }
  },

  async setItem<T>(key: PreferenceStorageKey, value: T): Promise<boolean> {
    try {
      await AsyncStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },

  async removeItem(key: PreferenceStorageKey): Promise<boolean> {
    try {
      await AsyncStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  },

  /** Clears only app-preference keys — never touches secure-storage-owned data. */
  async clearAll(): Promise<void> {
    await AsyncStorage.multiRemove(Object.values(PREFERENCE_STORAGE_KEYS));
  },
};
