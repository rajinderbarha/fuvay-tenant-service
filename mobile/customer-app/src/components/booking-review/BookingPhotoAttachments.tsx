import React, { useCallback, useState } from "react";
import { View, Image, Pressable, ActivityIndicator, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import {
  MAX_DRAFT_PHOTOS,
  ALLOWED_PHOTO_MIME_TYPES,
  type PickedPhoto,
} from "../../api/bookingPhotos/bookingPhotoApi";

export interface BookingPhotoAttachmentsProps {
  photoUrls: string[];
  /** Mutations are owned by the review controller (every draft mutation
   * goes through it); this component only picks the file and reports
   * failures. Both reject on failure so the error can be surfaced. */
  onAddPhoto: (photo: PickedPhoto) => Promise<void>;
  onRemovePhoto: (photoUrl: string) => Promise<void>;
  /** Attachments are part of the request being made; once it is confirmed
   * they are history, not something to edit. */
  editable?: boolean;
}

const THUMB = 72;

/** The draft stores a relative media path (`/v1/media/{id}/view`); an
 * <Image> needs an absolute URL. This lived here as a local helper, so the
 * rest of the app (category artwork, campaign banners, avatars) kept
 * hitting the same bug -- it now lives in domain/mediaUrl.ts and is shared. */
function absoluteUrl(url: string): string {
  return resolveMediaUrl(url) ?? url;
}

/** expo-image-picker gives a `mimeType` on newer SDKs and only a file
 * extension on older ones, so the type is derived defensively rather than
 * trusted -- the backend rejects anything outside jpg/png/webp with a 422. */
function resolveMimeType(asset: ImagePicker.ImagePickerAsset): string | null {
  const declared = asset.mimeType?.toLowerCase();
  if (declared && (ALLOWED_PHOTO_MIME_TYPES as readonly string[]).includes(declared)) {
    return declared;
  }
  const name = (asset.fileName ?? asset.uri).toLowerCase();
  if (name.endsWith(".png")) return "image/png";
  if (name.endsWith(".webp")) return "image/webp";
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
  return null;
}

/**
 * Lets the customer attach photos of the problem to their booking.
 *
 * This replaces a read-only "N photos attached" summary whose only action
 * was a link back to the assistant -- there was no way to actually add a
 * photo anywhere in the app, even though the backend has always supported
 * it. Showing someone the leak is often faster and more accurate than
 * describing it, and the provider sees it before they arrive.
 */
export function BookingPhotoAttachments({
  photoUrls,
  onAddPhoto,
  onRemovePhoto,
  editable = true,
}: BookingPhotoAttachmentsProps) {
  const { theme } = useTheme();
  const [busy, setBusy] = useState(false);

  const atLimit = photoUrls.length >= MAX_DRAFT_PHOTOS;

  const handleAdd = useCallback(async () => {
    if (busy || atLimit) return;

    // Permission is requested at the moment of use, not on mount -- an
    // unprompted permission dialog on a booking screen reads as hostile.
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "Photo access needed",
        "To attach a photo, allow photo access for this app in Settings.",
      );
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.7,
      allowsMultipleSelection: false,
    });
    if (picked.canceled || picked.assets.length === 0) return;

    const asset = picked.assets[0];
    const mimeType = resolveMimeType(asset);
    if (!mimeType) {
      Alert.alert("Unsupported image", "Please choose a JPG, PNG or WebP image.");
      return;
    }

    const photo: PickedPhoto = {
      uri: asset.uri,
      mimeType,
      fileName: asset.fileName ?? `booking-photo.${mimeType.split("/")[1]}`,
    };

    setBusy(true);
    try {
      await onAddPhoto(photo);
    } catch {
      Alert.alert("Couldn't attach photo", "Please check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }, [busy, atLimit, onAddPhoto]);

  const handleRemove = useCallback(
    async (photoUrl: string) => {
      if (busy) return;
      setBusy(true);
      try {
        await onRemovePhoto(photoUrl);
      } catch {
        Alert.alert("Couldn't remove photo", "Please check your connection and try again.");
      } finally {
        setBusy(false);
      }
    },
    [busy, onRemovePhoto],
  );

  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="labelStrong" color="secondary">Photos of the problem</AppText>
        <AppText variant="caption" color="tertiary">
          {photoUrls.length}/{MAX_DRAFT_PHOTOS}
        </AppText>
      </View>

      <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
        Optional. A photo helps your provider bring the right parts.
      </AppText>

      {photoUrls.length > 0 && (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs, marginTop: theme.spacing.sm }}>
          {photoUrls.map(url => (
            <View key={url} style={{ width: THUMB, height: THUMB }}>
              <Image
                source={{ uri: absoluteUrl(url) }}
                style={{ width: THUMB, height: THUMB, borderRadius: theme.radiusUsage.input, backgroundColor: theme.colors.surfaceDisabled }}
                accessibilityIgnoresInvertColors
              />
              {editable && (
                <Pressable
                  onPress={() => handleRemove(url)}
                  disabled={busy}
                  accessibilityRole="button"
                  accessibilityLabel="Remove this photo"
                  hitSlop={8}
                  style={{
                    position: "absolute", top: -6, right: -6,
                    width: 22, height: 22, borderRadius: 11,
                    alignItems: "center", justifyContent: "center",
                    backgroundColor: theme.colors.surfaceRaised,
                    borderWidth: 1, borderColor: theme.colors.borderDefault,
                  }}
                >
                  <Icon name="close" size="compact" color={theme.colors.textSecondary} decorative />
                </Pressable>
              )}
            </View>
          ))}
        </View>
      )}

      {editable && (
        <View style={{ marginTop: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
          <AppButton
            label={photoUrls.length === 0 ? "Add a photo" : "Add another"}
            tone="secondary"
            size="compact"
            onPress={handleAdd}
            disabled={busy || atLimit}
            disabledReason={atLimit ? `You can attach up to ${MAX_DRAFT_PHOTOS} photos.` : undefined}
          />
          {busy && <ActivityIndicator size="small" color={theme.colors.brandPrimaryStrong} />}
        </View>
      )}
    </AppCard>
  );
}
