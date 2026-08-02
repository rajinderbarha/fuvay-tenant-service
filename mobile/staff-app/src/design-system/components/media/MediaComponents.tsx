import React from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { ProgressBar } from "../feedback/Loading";

/**
 * Presentation-only media components (Phase D.14). None of these call the
 * actual camera/picker/upload APIs -- the real media service lands in
 * Phase F. These accept normalized view models and callbacks only, and
 * never assume a permanent public URL is the only media source (`uri` may
 * be a short-lived authorized/signed URL supplied by the later service).
 */

export function MediaPickerTrigger({ label = "Add photo", onPress, disabled }: { label?: string; onPress: () => void; disabled?: boolean }) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={{
        width: 88, height: 88, borderRadius: theme.radiusUsage.input, borderWidth: 2, borderStyle: "dashed",
        borderColor: theme.colors.borderStrong, alignItems: "center", justifyContent: "center", gap: 4,
        opacity: disabled ? theme.opacity.disabled : 1,
      }}
    >
      <Icon name="camera-outline" size="feature" color={theme.colors.textSecondary} decorative />
      <AppText variant="caption" color="secondary">{label}</AppText>
    </Pressable>
  );
}

export interface MediaPreviewModel {
  id: string;
  uri?: string;
  status: "pending" | "uploading" | "uploaded" | "failed";
  progress?: number;
}

export function MediaPreview({ media, onPressRemove, size = 88 }: { media: MediaPreviewModel; onPressRemove?: (id: string) => void; size?: number }) {
  const { theme } = useTheme();
  return (
    <View style={{ width: size, height: size, borderRadius: theme.radiusUsage.input, overflow: "hidden", backgroundColor: theme.colors.backgroundSunken }}>
      {media.uri ? <Image source={{ uri: media.uri }} style={{ width: size, height: size }} /> : null}
      {media.status === "uploading" ? (
        <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: 4, backgroundColor: theme.colors.backgroundOverlay }}>
          <ProgressBar progress={media.progress ?? 0} />
        </View>
      ) : null}
      {media.status === "failed" ? (
        <View style={{ position: "absolute", inset: 0, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.statusDangerSurface }}>
          <Icon name="alert-circle" size="standard" color={theme.colors.statusDanger} decorative />
        </View>
      ) : null}
      {onPressRemove ? (
        <Pressable
          onPress={() => onPressRemove(media.id)}
          accessibilityRole="button"
          accessibilityLabel="Remove photo"
          style={{ position: "absolute", top: 4, right: 4, width: 24, height: 24, borderRadius: 12, backgroundColor: theme.colors.backgroundOverlay, alignItems: "center", justifyContent: "center" }}
        >
          <Icon name="close" size="compact" color={theme.colors.textInverse} decorative />
        </Pressable>
      ) : null}
    </View>
  );
}

export function MediaUploadProgress({ progress }: { progress: number }) {
  return <ProgressBar progress={progress} />;
}

export function MediaUploadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
      <Icon name="alert-circle" size="compact" color={theme.colors.statusDanger} decorative />
      <AppText variant="caption" color="danger" style={{ flex: 1 }}>{message}</AppText>
      <AppText variant="caption" color="link" onPress={onRetry}>Retry</AppText>
    </View>
  );
}

export function EvidenceGrid({ items, onAdd, onRemove, maxItems }: {
  items: MediaPreviewModel[];
  onAdd?: () => void;
  onRemove?: (id: string) => void;
  maxItems?: number;
}) {
  const { theme } = useTheme();
  const canAddMore = onAdd && (maxItems === undefined || items.length < maxItems);
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
      {items.map(item => <MediaPreview key={item.id} media={item} onPressRemove={onRemove} />)}
      {canAddMore ? <MediaPickerTrigger onPress={onAdd!} /> : null}
    </View>
  );
}
