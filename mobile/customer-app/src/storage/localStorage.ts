import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * Non-sensitive local storage: presentation preferences (theme) and draft
 * form state only. Never write tokens or session material here -- use
 * src/storage/secureStorage.ts for that.
 */
export async function setLocalItem(key: string, value: string): Promise<void> {
  await AsyncStorage.setItem(key, value);
}

export async function getLocalItem(key: string): Promise<string | null> {
  return AsyncStorage.getItem(key);
}

export async function removeLocalItem(key: string): Promise<void> {
  await AsyncStorage.removeItem(key);
}

export async function setLocalJSON<T>(key: string, value: T): Promise<void> {
  await setLocalItem(key, JSON.stringify(value));
}

export async function getLocalJSON<T>(key: string): Promise<T | null> {
  const raw = await getLocalItem(key);
  if (raw === null) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}
