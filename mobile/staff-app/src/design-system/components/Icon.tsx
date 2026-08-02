import React from "react";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "../themes";
import { iconSizes, IconSizeToken } from "../tokens/iconSizes";

/**
 * One icon library only (Ionicons via @expo/vector-icons), for stroke-
 * weight consistency across the app. Never mix icon sets, never use emoji
 * as an operational icon.
 */
export interface IconProps {
  name: keyof typeof Ionicons.glyphMap;
  size?: IconSizeToken | number;
  color?: string;
  /** Accessible label -- required unless `decorative` is set, since an
   * icon with no adjacent text label is otherwise invisible to screen readers. */
  label?: string;
  decorative?: boolean;
}

export function Icon({ name, size = "standard", color, label, decorative }: IconProps) {
  const { theme } = useTheme();
  const resolvedSize = typeof size === "number" ? size : iconSizes[size];
  const resolvedColor = color ?? theme.colors.textPrimary;

  return (
    <Ionicons
      name={name}
      size={resolvedSize}
      color={resolvedColor}
      accessible={!decorative}
      accessibilityElementsHidden={decorative}
      importantForAccessibility={decorative ? "no-hide-descendants" : "yes"}
      accessibilityLabel={decorative ? undefined : label}
    />
  );
}
