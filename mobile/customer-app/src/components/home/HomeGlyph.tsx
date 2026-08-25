import React from "react";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "../../design-system/theme";
import type { IconSizeToken } from "../../design-system/tokens";

export type HomeGlyphName = keyof typeof MaterialCommunityIcons.glyphMap;

export function HomeGlyph({
  name,
  size = "standard",
  color,
  decorative = true,
}: {
  name: HomeGlyphName;
  size?: IconSizeToken;
  color?: string;
  decorative?: boolean;
}) {
  const { theme } = useTheme();
  return (
    <MaterialCommunityIcons
      name={name}
      size={theme.iconSizes[size]}
      color={color ?? theme.colors.textPrimary}
      accessibilityElementsHidden={decorative}
      importantForAccessibility={decorative ? "no-hide-descendants" : "auto"}
    />
  );
}
