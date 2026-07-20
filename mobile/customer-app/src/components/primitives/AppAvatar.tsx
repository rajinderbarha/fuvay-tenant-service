import React, { useState } from "react";
import { View, Image, ActivityIndicator } from "react-native";
import { AppText } from "./AppText";
import { AppIcon } from "./AppIcon";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { sizes } from "../../design-system/tokens/sizes";

export type AppAvatarSize = keyof typeof sizes.avatar;

export interface AppAvatarProps {
  imageUrl?: string | null;
  initials?: string;
  size?: AppAvatarSize;
  accessibilityLabel: string;
  loading?: boolean;
}

export function AppAvatar({ imageUrl, initials, size = "md", accessibilityLabel, loading }: AppAvatarProps) {
  const { theme } = useAppTheme();
  const [imageFailed, setImageFailed] = useState(false);
  const px = (theme.sizes.avatar as Record<AppAvatarSize, number>)[size];

  const containerStyle = {
    width: px,
    height: px,
    borderRadius: theme.radii.full,
    backgroundColor: theme.colors.surfaceSecondary,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    overflow: "hidden" as const,
  };

  return (
    <View style={containerStyle} accessible accessibilityRole="image" accessibilityLabel={accessibilityLabel}>
      {loading ? (
        <ActivityIndicator size="small" color={theme.colors.iconSecondary} />
      ) : imageUrl && !imageFailed ? (
        <Image source={{ uri: imageUrl }} style={{ width: px, height: px }} onError={() => setImageFailed(true)} />
      ) : initials ? (
        <AppText variant="titleMedium" color="textSecondary">
          {initials.slice(0, 2).toUpperCase()}
        </AppText>
      ) : (
        <AppIcon name="person" color="iconSecondary" />
      )}
    </View>
  );
}
