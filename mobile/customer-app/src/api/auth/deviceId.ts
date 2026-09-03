import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Crypto from "expo-crypto";

const DEVICE_ID_KEY = "serviceos.customerapp.device_id.v1";
let cached: string | null = null;

/** Stable, non-secret per-install identifier used for abuse controls and sessions. */
export async function getOrCreateDeviceId(): Promise<string> {
  if (cached) return cached;
  const stored = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (stored) {
    cached = stored;
    return stored;
  }
  const fresh = Crypto.randomUUID();
  await AsyncStorage.setItem(DEVICE_ID_KEY, fresh);
  cached = fresh;
  return fresh;
}
