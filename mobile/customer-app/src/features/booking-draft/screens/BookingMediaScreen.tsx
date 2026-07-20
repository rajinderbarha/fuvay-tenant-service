import React, { useState } from "react";
import { View, Image, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useDraft } from "../queries/draft-queries";
import { useDraftMedia, useUploadBookingPhoto, useDeleteMedia } from "../queries/media-queries";
import { useLinkDraftPhoto } from "../queries/draft-queries";
import { useMediaPicker, type PickedPhoto } from "../hooks/use-media-picker";
import { prepareImageForUpload } from "../hooks/prepare-image-for-upload";
import { validateMediaCandidate, MAX_BOOKING_PHOTOS_PER_DRAFT } from "../domain/media-validation";
import {
  createMediaItem,
  markInvalid,
  markUploading,
  markUploadFailed,
  markUploaded,
  markLinking,
  markLinkFailed,
  markLinked,
  type MediaItem,
} from "../domain/media-item";
import { resolveAuthorizedPreviewSource } from "../domain/media-preview-url";
import { logger } from "../../../observability/logger";
import { ApiError } from "../../../api/api-errors";
import type { RootStackParamList } from "../../../navigation/route-types";

type BookingMediaRouteProp = RouteProp<RootStackParamList, "BookingMedia">;

let localIdCounter = 0;
function nextLocalId(): string {
  localIdCounter += 1;
  return `local-${Date.now()}-${localIdCounter}`;
}

/**
 * The real production media step (CUSTOMER-L5-06). Uploads via the Phase
 * 0A media engine (`media_context="booking_issue_photo"`), then links the
 * resulting asset's URL to the draft via the real, append-only
 * `POST /photos` endpoint — see CUSTOMER-L5-06-upload-lifecycle.md. Media
 * is optional in this sprint: no offering-level "requires photo" flag is
 * authoritative here (see known-gaps.md), so no hard block is imposed
 * before continuing.
 */
export function BookingMediaScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<BookingMediaRouteProp>();
  const { draftId } = route.params;

  const draft = useDraft(draftId);
  const draftMedia = useDraftMedia(draftId);
  const uploadPhoto = useUploadBookingPhoto();
  const linkPhoto = useLinkDraftPhoto();
  const deleteMedia = useDeleteMedia();
  const { pickFromCamera, pickFromGallery } = useMediaPicker();

  const [localItems, setLocalItems] = useState<MediaItem[]>([]);

  const linkedCount = draft.data?.photo_urls.length ?? 0;
  const atLimit = linkedCount >= MAX_BOOKING_PHOTOS_PER_DRAFT;

  function updateItem(localId: string, updater: (item: MediaItem) => MediaItem) {
    setLocalItems((prev) => prev.map((item) => (item.localId === localId ? updater(item) : item)));
  }

  async function handlePicked(photo: PickedPhoto) {
    const localId = nextLocalId();
    const candidate = { uri: photo.uri, mimeType: photo.mimeType, fileSizeBytes: photo.fileSizeBytes };
    const failure = validateMediaCandidate(candidate, linkedCount);
    let item = createMediaItem(localId, photo.uri, photo.mimeType, photo.fileSizeBytes);

    if (failure) {
      logger.info("media_validation_failed", { reason: failure });
      setLocalItems((prev) => [...prev, markInvalid(item, failure)]);
      return;
    }
    setLocalItems((prev) => [...prev, item]);

    try {
      const prepared = await prepareImageForUpload(photo);
      updateItem(localId, markUploading);
      logger.info("upload_started", {});
      const asset = await uploadPhoto.mutateAsync({
        draftId,
        file: { uri: prepared.uri, name: `photo-${localId}.jpg`, type: prepared.mimeType },
      });
      item = markUploaded(item, asset.id);
      updateItem(localId, () => item);

      updateItem(localId, markLinking);
      await linkPhoto.mutateAsync({ draftId, photoUrl: asset.preview_url, contentType: asset.mime_type });
      updateItem(localId, markLinked);
      logger.info("media_step_completed", {});
      void draftMedia.refetch();
    } catch (err) {
      const category = err instanceof ApiError ? err.category : "unknown";
      logger.warn("upload_failed", { category });
      updateItem(localId, (current) => (current.status === "UPLOADING" ? markUploadFailed(current, category) : markLinkFailed(current, category)));
    }
  }

  async function handleDeleteLinked(mediaId: string) {
    try {
      await deleteMedia.mutateAsync({ mediaId, draftId });
    } catch (err) {
      logger.warn("media_delete_failed", { category: err instanceof ApiError ? err.category : "unknown" });
    }
  }

  if (draft.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="60%" />
          <Skeleton height={120} />
        </View>
      </SafeAreaView>
    );
  }

  if (draft.isError || !draft.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("draft.loadError")} onRetry={() => void draft.refetch()} />
        </View>
      </SafeAreaView>
    );
  }

  const inProgressItems = localItems.filter((item) => item.status !== "LINKED");

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("media.title")}
          </AppText>
        </View>

        <AppText variant="bodySmall" color="textSecondary">
          {t("media.helperOptional")}
        </AppText>

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing[3] }}>
          {(draftMedia.data ?? []).map((asset) => (
            <LinkedThumbnail key={asset.id} previewUrl={asset.preview_url} onDelete={() => void handleDeleteLinked(asset.id)} removeLabel={t("media.remove")} />
          ))}
          {inProgressItems.map((item) => (
            <PendingThumbnail key={item.localId} item={item} t={t} />
          ))}
        </View>

        {!atLimit ? (
          <View style={{ flexDirection: "row", gap: theme.spacing[3] }}>
            <AppButton
              label={t("media.takePhoto")}
              onPress={async () => {
                const result = await pickFromCamera();
                if (result.outcome === "picked") await handlePicked(result.photo);
                else if (result.outcome === "permission_denied") logger.info("media_picker_permission_denied", { source: "camera" });
              }}
              variant="secondary"
              size="medium"
            />
            <AppButton
              label={t("media.chooseFromGallery")}
              onPress={async () => {
                const result = await pickFromGallery();
                if (result.outcome === "picked") await handlePicked(result.photo);
                else if (result.outcome === "permission_denied") logger.info("media_picker_permission_denied", { source: "gallery" });
              }}
              variant="secondary"
              size="medium"
            />
          </View>
        ) : (
          <AppText variant="caption" color="textTertiary">
            {t("media.maxReached")}
          </AppText>
        )}

        <View style={{ flex: 1 }} />

        <AppButton
          label={t("media.continue")}
          onPress={() => navigation.navigate("AddressSelection", { draftId })}
          variant="primary"
          size="large"
          testID="media-continue-button"
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function LinkedThumbnail({ previewUrl, onDelete, removeLabel }: { previewUrl: string; onDelete: () => void; removeLabel: string }) {
  const { theme } = useAppTheme();
  const [source, setSource] = useState<{ uri: string; headers: Record<string, string> } | null>(null);

  React.useEffect(() => {
    void resolveAuthorizedPreviewSource(previewUrl).then(setSource);
  }, [previewUrl]);

  return (
    <View style={{ width: 84, height: 84, borderRadius: theme.radii.md, overflow: "hidden", backgroundColor: theme.colors.surfaceSecondary }}>
      {source ? <Image source={source} style={{ width: 84, height: 84 }} resizeMode="cover" /> : null}
      <AppPressable
        accessibilityLabel={removeLabel}
        onPress={onDelete}
        style={{ position: "absolute", top: 2, right: 2, backgroundColor: theme.colors.scrim, borderRadius: theme.radii.full }}
      >
        <AppIcon name="close-circle" size="sm" color="iconInverse" />
      </AppPressable>
    </View>
  );
}

function PendingThumbnail({ item, t }: { item: MediaItem; t: (key: string) => string }) {
  const { theme } = useAppTheme();
  const label =
    item.status === "INVALID"
      ? item.validationFailure === "TOO_LARGE"
        ? t("media.fileTooLarge")
        : item.validationFailure === "UNSUPPORTED_TYPE"
          ? t("media.unsupportedFile")
          : t("media.uploadFailed")
      : item.status === "UPLOAD_FAILED" || item.status === "LINK_FAILED"
        ? t("media.uploadFailed")
        : t("media.uploading");

  return (
    <View
      style={{
        width: 84,
        height: 84,
        borderRadius: theme.radii.md,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        alignItems: "center",
        justifyContent: "center",
        padding: theme.spacing[2],
      }}
    >
      <Image source={{ uri: item.uri }} style={{ width: 84, height: 84, position: "absolute", opacity: 0.4 }} resizeMode="cover" />
      <AppText variant="caption" color="textSecondary" align="center">
        {label}
      </AppText>
    </View>
  );
}
