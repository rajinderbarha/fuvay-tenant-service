import React from "react";
import { Pressable, View } from "react-native";

import { useTheme } from "../design-system/theme";
import { AppLucideIcon, type AppLucideName } from "./AppLucideIcon";
import { AppSurface } from "./AppSurface";

export type AppIconTileTone = "brand" | "success" | "warning" | "danger" | "info" | "violet" | "cyan" | "mint" | "coral" | "amber" | "neutral";
export type AppIconTileShape = "circle" | "squircle";

export interface AppIconTileProps {
  name: AppLucideName;
  size?: number;
  tone?: AppIconTileTone;
  shape?: AppIconTileShape;
  emphasized?: boolean;
  onPress?: () => void;
  accessibilityLabel?: string;
}

function toneColor(theme: ReturnType<typeof useTheme>["theme"], tone: AppIconTileTone) {
  switch (tone) {
    case "success": return theme.colors.statusSuccess;
    case "warning": return theme.colors.statusWarning;
    case "danger": return theme.colors.statusDanger;
    case "info": return theme.colors.statusInfo;
    case "violet": return theme.colors.accentViolet;
    case "cyan": return theme.colors.accentCyan;
    case "mint": return theme.colors.accentMint;
    case "coral": return theme.colors.accentCoral;
    case "amber": return theme.colors.accentAmber;
    case "neutral": return theme.colors.iconDefault;
    default: return theme.colors.brandPrimaryStrong;
  }
}

/** Layered Lucide tile matching the supplied Circle Tile reference. */
export function AppIconTile({
  name,
  size = 48,
  tone = "brand",
  shape = "squircle",
  emphasized = false,
  onPress,
  accessibilityLabel,
}: AppIconTileProps) {
  const { theme } = useTheme();
  const accent = toneColor(theme, tone);
  const radius = shape === "circle" ? size / 2 : Math.round(size * 0.28);
  const inset = emphasized ? Math.max(4, Math.round(size * 0.09)) : Math.max(3, Math.round(size * 0.07));
  const iconSize = Math.round(size * (emphasized ? 0.42 : 0.38));

  const tile = (
    <AppSurface
      colors={theme.material.tileOuter}
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        padding: inset,
        borderColor: emphasized ? accent : theme.material.outline,
        borderWidth: emphasized ? 1.5 : 1,
      }}
    >
      <AppSurface
        colors={theme.material.tileInner}
        elevated={false}
        style={{
          flex: 1,
          borderRadius: Math.max(1, radius - inset),
          alignItems: "center",
          justifyContent: "center",
          borderColor: emphasized ? `${accent}66` : theme.material.outline,
        }}
      >
        <AppLucideIcon name={name} size={iconSize} color={accent} strokeWidth={1.75} />
      </AppSurface>
    </AppSurface>
  );

  if (!onPress) return tile;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      hitSlop={8}
      style={({ pressed }) => ({ opacity: pressed ? 0.76 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] })}
    >
      {tile}
    </Pressable>
  );
}

