import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { authenticatedRequest } from "../api/authenticatedClient";

const DEVICE_ID_KEY = "staff_app_push_device_id";

/** Stable per-installation device id (spec section 6: "bind token to the
 * current installation/device") -- generated once, persisted locally.
 * Deliberately not a hardware identifier; this app has no need for one and
 * avoids the extra native permission that would require. */
async function getOrCreateDeviceId(): Promise<string> {
  const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (existing) return existing;
  const generated = `${Platform.OS}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  await AsyncStorage.setItem(DEVICE_ID_KEY, generated);
  return generated;
}

export type PushPermissionState = "granted" | "denied" | "undetermined";

export async function getPushPermissionState(): Promise<PushPermissionState> {
  try {
    const { status } = await Notifications.getPermissionsAsync();
    return status as PushPermissionState;
  } catch {
    return "undetermined";
  }
}

/** Registers (or replaces, on token rotation) this device's Expo push token
 * with the backend (spec section 6). Never throws -- push registration
 * failing must not block sign-in or app usage. Does NOT repeatedly prompt
 * after a prior denial: only requests permission if not yet determined. */
export async function registerPushDevice(): Promise<{ ok: boolean; permission: PushPermissionState }> {
  try {
    const existing = await Notifications.getPermissionsAsync();
    let status = existing.status;
    if (status === "undetermined") {
      const requested = await Notifications.requestPermissionsAsync();
      status = requested.status;
    }
    if (status !== "granted") {
      return { ok: false, permission: status as PushPermissionState };
    }

    const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
    const tokenResult = await Notifications.getExpoPushTokenAsync(projectId ? { projectId } : undefined);
    const deviceId = await getOrCreateDeviceId();

    const result = await authenticatedRequest(`/v1/staff/push-devices`, {
      method: "POST",
      body: {
        device_id: deviceId, expo_push_token: tokenResult.data,
        platform: Platform.OS, app_version: Constants.expoConfig?.version ?? null,
      },
    });
    return { ok: result.ok, permission: "granted" };
  } catch {
    return { ok: false, permission: "undetermined" };
  }
}

/** Revokes this device's registration (spec section 6: "Revoke token on
 * sign-out"). Best-effort -- sign-out must proceed even if this fails. */
export async function revokePushDevice(): Promise<void> {
  try {
    const deviceId = await AsyncStorage.getItem(DEVICE_ID_KEY);
    if (!deviceId) return;
    await authenticatedRequest(`/v1/staff/push-devices/current`, { method: "DELETE", body: { device_id: deviceId } });
  } catch {
    // Best-effort -- sign-out proceeds regardless.
  }
}
