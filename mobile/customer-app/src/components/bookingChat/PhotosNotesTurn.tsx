import React, { useCallback, useState } from "react";
import { View, Image, Pressable, ActivityIndicator, Alert, TextInput } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotPrimaryButton } from "./BotPrimitives";
import { resolveMediaImageSource } from "../../domain/mediaUrl";
import { MAX_DRAFT_PHOTOS, ALLOWED_PHOTO_MIME_TYPES, type PickedPhoto } from "../../api/bookingPhotos/bookingPhotoApi";
import { getInMemoryAccessToken } from "../../api/session/tokenVault";
import { BotText } from "./BotText";
import { useTheme } from "../../design-system/theme";
import { AppLucideIcon } from "../AppLucideIcon";

export interface PhotosNotesTurnProps {
  photoUrls: string[];
  onAddPhoto: (photo: PickedPhoto) => Promise<void>;
  onRemovePhoto: (photoUrl: string) => Promise<void>;
  onContinue: () => void;
  summaryChips?: string[];
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
export function PhotosNotesTurn({ photoUrls, onAddPhoto, onRemovePhoto, onContinue, summaryChips = [] }: PhotosNotesTurnProps) {
  const BOT = useBotColors();
  const { theme } = useTheme();
  const f = theme.fuvay;
  const [busy, setBusy] = useState(false);
  const [pendingPreviewUri, setPendingPreviewUri] = useState<string | null>(null);
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
    // Show the device image immediately. The server remains authoritative for
    // whether it is attached, but a Cloudinary round-trip must not leave the
    // customer wondering whether their tap worked.
    setPendingPreviewUri(asset.uri);
    setBusy(true);
    try { await onAddPhoto(photo); } catch { Alert.alert("Couldn't attach photo", "Please check your connection and try again."); }
    finally { setBusy(false); setPendingPreviewUri(null); }
  }, [busy, atLimit, onAddPhoto]);

  const handleRemove = useCallback(async (url: string) => {
    if (busy) return;
    setBusy(true);
    try { await onRemovePhoto(url); } catch { Alert.alert("Couldn't remove photo", "Please check your connection and try again."); }
    finally { setBusy(false); }
  }, [busy, onRemovePhoto]);

  return (
    <View style={{ gap: 18 }}>
      <BotText style={{ fontSize: 22, lineHeight: 27, fontWeight: "700", color: BOT.textPrimary }}>Anything else we should know?</BotText>
      <BotText style={{ fontSize: 11.5, lineHeight: 17, color: BOT.textMuted, marginTop: -10 }}>Optional. A short note helps the technician arrive prepared.</BotText>
      {summaryChips.length ? <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>{summaryChips.slice(0, 4).map(chip => <View key={chip} style={{ minHeight: 32, paddingHorizontal: 12, borderRadius: 16, backgroundColor: f.soft(f.accents.a3), flexDirection: "row", alignItems: "center", gap: 6 }}><AppLucideIcon name="check" size={12} color={f.accents.a3} /><BotText style={{ fontSize: 11.5, color: f.accents.a3 }}>{chip}</BotText></View>)}</View> : null}
      <TextInput accessibilityLabel="Additional booking note" multiline placeholder="e.g. Outdoor unit is on the balcony, gate code 4412" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 128, textAlignVertical: "top", borderRadius: 18, padding: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />

      {photoUrls.length > 0 || pendingPreviewUri ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
          {pendingPreviewUri ? (
            <View style={{ width: THUMB, height: THUMB }}>
              <Image
                source={{ uri: pendingPreviewUri }}
                accessibilityLabel="Photo uploading"
                style={{ width: THUMB, height: THUMB, borderRadius: 10, backgroundColor: BOT.surfaceRaised, opacity: 0.82 }}
              />
              <ActivityIndicator
                size="small"
                color={BOT.brand}
                style={{ position: "absolute", top: 22, left: 22 }}
              />
            </View>
          ) : null}
          {photoUrls.map(url => (
            <View key={url} style={{ width: THUMB, height: THUMB }}>
              <Image
                source={resolveMediaImageSource(url, getInMemoryAccessToken()) ?? { uri: url }}
                accessibilityLabel="Photo attached"
                style={{ width: THUMB, height: THUMB, borderRadius: 10, backgroundColor: BOT.surfaceRaised }}
              />
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

      <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
        <Pressable
          onPress={handleAdd}
          disabled={busy || atLimit}
          accessibilityRole="button"
          accessibilityLabel={photoUrls.length === 0 ? "Add a photo" : "Add another photo"}
          style={{ flex: 1, height: 44, paddingHorizontal: 14, borderRadius: 14, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 6, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border, opacity: atLimit ? 0.5 : 1 }}
        >
          <Ionicons name="attach-outline" size={15} color={BOT.textSecondary} />
          <BotText style={{ fontSize: 11.5, fontWeight: "600", color: BOT.textSecondary }}>{photoUrls.length === 0 ? "Add photo" : "Add another"}</BotText>
        </Pressable>
        <Pressable accessibilityRole="button" accessibilityLabel="Add voice note" style={{ flex: 1, height: 44, paddingHorizontal: 14, borderRadius: 14, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 6, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border }}><AppLucideIcon name="mic" size={14} color={f.surfaces.sub} /><BotText style={{ fontSize: 11.5, fontWeight: "600", color: BOT.textSecondary }}>Voice note</BotText></Pressable>
        {busy ? <ActivityIndicator size="small" color={BOT.brand} /> : null}
      </View>

      <View style={{ marginTop: 4 }}>
        <BotPrimaryButton label="Get my price  →" onPress={onContinue} />
      </View>
    </View>
  );
}
