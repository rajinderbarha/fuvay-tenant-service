import React from "react";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "../design-system/theme";
import { IconSizeToken } from "../design-system/tokens";

export interface IconProps {
  name: keyof typeof Ionicons.glyphMap;
  size?: IconSizeToken;
  color?: string;
  /** Purely decorative icons (paired with adjacent text) are hidden from
   * screen readers; icons that are the only affordance must pass a label
   * via the parent Pressable's accessibilityLabel instead. */
  decorative?: boolean;
}

export function Icon({ name, size = "standard", color, decorative }: IconProps) {
  const { theme } = useTheme();
  const px = theme.iconSizes[size];
  return (
    <Ionicons
      name={name}
      size={px}
      color={color ?? theme.colors.textPrimary}
      accessibilityElementsHidden={decorative}
      importantForAccessibility={decorative ? "no-hide-descendants" : "auto"}
    />
  );
}
