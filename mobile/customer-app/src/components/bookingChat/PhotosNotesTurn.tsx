import React, { useCallback, useState } from "react";
import { View, Text, Image, Pressable, ActivityIndicator, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotCard, BotPrimaryButton } from "./BotPrimitives";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { MAX_DRAFT_PHOTOS, ALLOWED_PHOTO_MIME_TYPES, type PickedPhoto } from "../../api/bookingPhotos/bookingPhotoApi";

export interface PhotosNotesTurnProps {
  photoUrls: string[];
  onAddPhoto: (photo: PickedPhoto) => Promise<void>;
  onRemovePhoto: (photoUrl: string) => Promise<void>;
  onContinue: () => void;
}

const THUMB = 64;

function resolveMimeType(asset: ImagePicker.ImagePickerAsset): string | null {
  const declared = asset.mimeType?.toLowerCase();
  if (declared && (ALLOWED_PHOTO_MIME_TYPES as readonly string[]).includes(declared)) return declared;
  const name = (asset.fileName ?? asset.uri).toLowerCase();
  if (name.endsWith(".png")) return "image/png";
  if (name.endsWith(".webp")) return "image/webp";
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
  return null;
}

/** Reuses the exact same photo endpoints as the old Review screen
 * (BookingPhotoAttachments) -- only the visual shell changed. Free-text
 * "additional detail" is NOT a separate step here: it is already the
 * catalog's own `issue_detail` text question, answered earlier in the
 * normal question loop like any other question. */
export function PhotosNotesTurn({ photoUrls, onAddPhoto, onRemovePhoto, onContinue }: PhotosNotesTurnProps) {
  const BOT = useBotColors();
  const [busy, setBusy] = useState(false);
  const atLimit = photoUrls.length >= MAX_DRAFT_PHOTOS;

  const handleAdd = useCallback(async () => {
    if (busy || atLimit) return;
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Photo access needed", "To attach a photo, allow photo access for this app in Settings.");
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.7, allowsMultipleSelection: false });
    if (picked.canceled || picked.assets.length === 0) return;
    const asset = picked.assets[0];
    const mimeType = resolveMimeType(asset);
    if (!mimeType) {
      Alert.alert("Unsupported image", "Please choose a JPG, PNG or WebP image.");
      return;
    }
    const photo: PickedPhoto = { uri: asset.uri, mimeType, fileName: asset.fileName ?? `booking-photo.${mimeType.split("/")[1]}` };
    setBusy(true);
    try { await onAddPhoto(photo); } catch { Alert.alert("Couldn't attach photo", "Please check your connection and try again."); }
    finally { setBusy(false); }
  }, [busy, atLimit, onAddPhoto]);

  const handleRemove = useCallback(async (url: string) => {
    if (busy) return;
    setBusy(true);
    try { await onRemovePhoto(url); } catch { Alert.alert("Couldn't remove photo", "Please check your connection and try again."); }
    finally { setBusy(false); }
  }, [busy, onRemovePhoto]);

  return (
    <BotCard>
      <Text style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>Add a photo? (optional)</Text>
      <Text style={{ fontSize: 13, color: BOT.textMuted, marginTop: 2 }}>
        A photo helps your provider bring the right parts.
      </Text>

      {photoUrls.length > 0 ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {photoUrls.map(url => (
            <View key={url} style={{ width: THUMB, height: THUMB }}>
              <Image source={{ uri: resolveMediaUrl(url) ?? url }} style={{ width: THUMB, height: THUMB, borderRadius: 10, backgroundColor: BOT.surfaceRaised }} />
              <Pressable
                onPress={() => handleRemove(url)}
                disabled={busy}
                accessibilityRole="button"
                accessibilityLabel="Remove this photo"
                hitSlop={8}
                style={{ position: "absolute", top: -6, right: -6, width: 20, height: 20, borderRadius: 10, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border }}
              >
                <Ionicons name="close" size={12} color={BOT.textSecondary} />
              </Pressable>
            </View>
          ))}
        </View>
      ) : null}

      <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginTop: 12 }}>
        <Pressable
          onPress={handleAdd}
          disabled={busy || atLimit}
          accessibilityRole="button"
          accessibilityLabel={photoUrls.length === 0 ? "Add a photo" : "Add another photo"}
          style={{ height: 36, paddingHorizontal: 14, borderRadius: 18, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 6, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border, opacity: atLimit ? 0.5 : 1 }}
        >
          <Ionicons name="camera-outline" size={15} color={BOT.textSecondary} />
          <Text style={{ fontSize: 13, color: BOT.textSecondary }}>{photoUrls.length === 0 ? "Add a photo" : "Add another"}</Text>
        </Pressable>
        {busy ? <ActivityIndicator size="small" color={BOT.brand} /> : null}
      </View>

      <View style={{ marginTop: 14 }}>
        <BotPrimaryButton label="Continue" onPress={onContinue} />
      </View>
    </BotCard>
  );
}
