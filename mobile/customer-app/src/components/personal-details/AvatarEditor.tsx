import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface AvatarEditorProps {
  name: string;
  avatarUrl: string | null;
  /** No camera badge, no "Change photo" action, no file-limit copy when
   * false -- no upload contract is confirmed this phase (spec section 6:
   * "If no contract exists: hide camera badge, Change photo and
   * file-limit copy"). */
  canUpdateAvatar: boolean;
  onChangePhoto?: () => void;
}

export function AvatarEditor({ name, avatarUrl, canUpdateAvatar, onChangePhoto }: AvatarEditorProps) {
  const { theme } = useTheme();
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <View style={{ alignItems: "center", gap: theme.spacing.xxs }}>
      <View style={{ width: 96, height: 96 }}>
        <View
          accessibilityRole="image"
          accessibilityLabel={`${name}'s profile photo`}
          style={{
            width: 96, height: 96, borderRadius: theme.radius.radiusFull, overflow: "hidden",
            backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
            borderWidth: 1, borderColor: theme.colors.borderSubtle,
          }}
        >
          {avatarUrl ? (
            <Image source={{ uri: avatarUrl }} style={{ width: "100%", height: "100%" }} />
          ) : (
            <AppText variant="title" color="secondary">{initial}</AppText>
          )}
        </View>
        {canUpdateAvatar ? (
          <View
            accessibilityElementsHidden
            style={{
              position: "absolute", bottom: 0, right: 0, width: 28, height: 28, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.brandPrimary, alignItems: "center", justifyContent: "center",
              borderWidth: 2, borderColor: theme.colors.surfaceDefault,
            }}
          >
            <Icon name="camera" size="compact" color={theme.colors.brandOnPrimary} decorative />
          </View>
        ) : null}
      </View>
      {canUpdateAvatar ? (
        <>
          <AppText
            variant="labelStrong" color="link" onPress={onChangePhoto}
            accessibilityRole="button" accessibilityLabel="Change photo"
          >
            Change photo
          </AppText>
          <AppText variant="caption" color="tertiary">JPG or PNG · Max 5 MB</AppText>
        </>
      ) : null}
    </View>
  );
}
