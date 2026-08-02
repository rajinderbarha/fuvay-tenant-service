import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Crypto from "expo-crypto";

/**
 * A stable per-install device identifier (Phase G: "trust this device"
 * only means something if the same device_id is sent on every login from
 * this install). This is NOT sensitive session material -- it identifies
 * the installation, not the user or their credentials -- so, per Phase F's
 * storage classification (spec section 5), it correctly lives in
 * AsyncStorage, not SecureStore.
 */
const DEVICE_ID_KEY = "serviceos.staffapp.device_id.v1";
let cached: string | null = null;

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
