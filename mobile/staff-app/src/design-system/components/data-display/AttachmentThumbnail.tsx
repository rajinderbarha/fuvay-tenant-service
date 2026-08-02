import React from "react";
import { View, Image, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { Icon } from "../Icon";
import { AppText } from "../typography/AppText";

export interface AttachmentThumbnailProps {
  /** Authorized preview URI (short-lived/signed) -- never a permanent
   * public URL. Presentation only; the media service (Phase F) resolves
   * this URI. */
  uri?: string;
  label?: string;
  onPress?: () => void;
  size?: number;
}

export function AttachmentThumbnail({ uri, label, onPress, size = 64 }: AttachmentThumbnailProps) {
  const { theme } = useTheme();
  const content = (
    <View
      style={{
        width: size, height: size, borderRadius: theme.radiusUsage.input, overflow: "hidden",
        backgroundColor: theme.colors.backgroundSunken, alignItems: "center", justifyContent: "center",
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      {uri ? <Image source={{ uri }} style={{ width: size, height: size }} /> : <Icon name="image-outline" size="feature" color={theme.colors.textTertiary} decorative />}
    </View>
  );

  return (
    <View style={{ alignItems: "center", gap: 4 }}>
      {onPress ? (
        <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label ?? "View attachment"}>{content}</Pressable>
      ) : content}
      {label ? <AppText variant="caption" color="tertiary" numberOfLines={1}>{label}</AppText> : null}
    </View>
  );
}
