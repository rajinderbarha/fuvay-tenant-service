import React from "react";
import { Ionicons } from "@expo/vector-icons";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import type { SemanticColors } from "../../design-system/themes/theme-types";

/**
 * The one sanctioned icon entry point for application code. Wraps
 * @expo/vector-icons/Ionicons — do not import a second icon package.
 */
export const ICON_NAMES = [
  "home",
  "list",
  "chatbubble",
  "person",
  "checkmark-circle",
  "close-circle",
  "alert-circle",
  "information-circle",
  "star",
  "chevron-forward",
  "chevron-back",
  "close",
  "add",
  "search",
  "settings",
  "notifications",
  "location",
  "cloud-offline",
  "reload",
] as const;

export type IconName = (typeof ICON_NAMES)[number];
export type IconSize = "xs" | "sm" | "md" | "lg" | "xl";
export type IconSemanticColor = keyof Pick<
  SemanticColors,
  "iconPrimary" | "iconSecondary" | "iconInverse" | "iconDisabled" | "iconSuccess" | "iconWarning" | "iconDanger"
>;

export interface AppIconProps {
  name: IconName;
  size?: IconSize;
  color?: IconSemanticColor;
  /** Set when the icon conveys meaning on its own (e.g. inside an icon-only button's accessibilityLabel owner). Decorative icons are hidden from screen readers by default. */
  accessibilityLabel?: string;
}

export function AppIcon({ name, size = "md", color = "iconPrimary", accessibilityLabel }: AppIconProps) {
  const { theme } = useAppTheme();
  const px = theme.sizes.icon;

  return (
    <Ionicons
      name={name}
      size={px[size]}
      color={theme.colors[color]}
      accessibilityElementsHidden={!accessibilityLabel}
      importantForAccessibility={accessibilityLabel ? "yes" : "no-hide-descendants"}
      accessibilityLabel={accessibilityLabel}
    />
  );
}
