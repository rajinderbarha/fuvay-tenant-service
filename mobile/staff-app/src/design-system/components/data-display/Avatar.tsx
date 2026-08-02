import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";

export interface AvatarProps {
  name: string;
  imageUri?: string;
  size?: number;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return parts.slice(0, 2).map(p => p[0]?.toUpperCase()).join("");
}

export function Avatar({ name, imageUri, size = 40 }: AvatarProps) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="image"
      accessibilityLabel={name}
      style={{
        width: size, height: size, borderRadius: theme.radiusUsage.avatar,
        backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center", overflow: "hidden",
      }}
    >
      {imageUri ? (
        <Image source={{ uri: imageUri }} style={{ width: size, height: size }} />
      ) : (
        <AppText variant="labelStrong" style={{ color: theme.colors.brandPrimaryPressed, fontSize: size * 0.4 }}>
          {initials(name)}
        </AppText>
      )}
    </View>
  );
}
