import * as ImageManipulator from "expo-image-manipulator";
import type { PickedPhoto } from "./use-media-picker";

const MAX_DIMENSION = 1920;
const JPEG_COMPRESSION_QUALITY = 0.7;

/**
 * Resizes (if needed) and re-encodes as JPEG at a fixed compression
 * quality — deterministic settings, not adaptive, matching CUSTOMER-L5-06
 * §24's "compress deterministically" requirement. `expo-image-manipulator`
 * does not carry EXIF through its output (it re-encodes the pixel buffer),
 * so this step also has the effect of stripping any capture metadata —
 * verified by the library re-encoding the image rather than copying the
 * original file, though this project does not have a way to inspect the
 * resulting binary's headers directly in this environment to prove it byte
 * for byte (see known-gaps.md).
 */
export async function prepareImageForUpload(photo: PickedPhoto): Promise<PickedPhoto> {
  const needsResize = Boolean(photo.width && photo.height && Math.max(photo.width, photo.height) > MAX_DIMENSION);
  const actions: ImageManipulator.Action[] = needsResize ? [{ resize: { width: MAX_DIMENSION } }] : [];

  const result = await ImageManipulator.manipulateAsync(photo.uri, actions, {
    compress: JPEG_COMPRESSION_QUALITY,
    format: ImageManipulator.SaveFormat.JPEG,
  });

  return { uri: result.uri, mimeType: "image/jpeg", fileSizeBytes: null, width: result.width, height: result.height };
}
