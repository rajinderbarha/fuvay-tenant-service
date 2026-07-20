import { useCallback } from "react";
import * as ImagePicker from "expo-image-picker";
import { logger } from "../../../observability/logger";

export type PickedPhoto = { uri: string; mimeType: string; fileSizeBytes: number | null; width: number | null; height: number | null };

export type MediaPickerOutcome = { outcome: "picked"; photo: PickedPhoto } | { outcome: "cancelled" } | { outcome: "permission_denied" };

/**
 * Camera and gallery selection via `expo-image-picker` — the one media
 * library already installed in this app. No `exif` option is passed (its
 * default is `false`), which means EXIF/GPS data is never even read off
 * the asset in the first place, not merely stripped afterward
 * (CUSTOMER-L5-06 §25's privacy-safe default, satisfied by simply not
 * opting in to a feature that defaults off). Permission is requested at
 * point of use, never at startup (CUSTOMER-L5-06 §55).
 */
export function useMediaPicker() {
  const pickFromCamera = useCallback(async (): Promise<MediaPickerOutcome> => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      logger.info("media_picker_permission_denied", { source: "camera" });
      return { outcome: "permission_denied" };
    }
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.8 });
    return toOutcome(result);
  }, []);

  const pickFromGallery = useCallback(async (): Promise<MediaPickerOutcome> => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      logger.info("media_picker_permission_denied", { source: "gallery" });
      return { outcome: "permission_denied" };
    }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    return toOutcome(result);
  }, []);

  return { pickFromCamera, pickFromGallery };
}

function toOutcome(result: ImagePicker.ImagePickerResult): MediaPickerOutcome {
  if (result.canceled || result.assets.length === 0) return { outcome: "cancelled" };
  const asset = result.assets[0];
  return {
    outcome: "picked",
    photo: {
      uri: asset.uri,
      mimeType: asset.mimeType ?? "application/octet-stream",
      fileSizeBytes: asset.fileSize ?? null,
      width: asset.width ?? null,
      height: asset.height ?? null,
    },
  };
}
