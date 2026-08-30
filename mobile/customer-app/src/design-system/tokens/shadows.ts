import { ViewStyle } from "react-native";

/**
 * Elevation — Fuvay v2.
 *
 * v2 shadows are warm in light mode (#3c342c, matching the warm neutral
 * shell) rather than the cool slate the previous palette used; a cool shadow
 * under a warm off-white card reads as dirty grey. Dark mode uses pure black
 * at high opacity, as the canvas does.
 *
 * `tile` is the neumorphic tile drop — deeper and tighter than `md`, and
 * always paired with the inner highlight from MaterialTokens so the tile
 * reads as raised rather than merely shadowed.
 */
export function buildShadows(
  mode: "light" | "dark",
): Record<"sm" | "md" | "lg" | "tile", ViewStyle> {
  const dark = mode === "dark";
  const shadowColor = dark ? "#000000" : "#3c342c";
  return {
    sm: {
      shadowColor,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: dark ? 0.3 : 0.08,
      shadowRadius: 5,
      elevation: 2,
    },
    // The canvas's `softShadow`: 0 8px 16px -8px.
    md: {
      shadowColor,
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: dark ? 0.55 : 0.2,
      shadowRadius: 16,
      elevation: 5,
    },
    // The canvas's `shellShadow`: 0 34px 60px -20px.
    lg: {
      shadowColor,
      shadowOffset: { width: 0, height: 20 },
      shadowOpacity: dark ? 0.8 : 0.35,
      shadowRadius: 30,
      elevation: 12,
    },
    // The canvas's `tileShadow`: 0 10px 16px -8px.
    tile: {
      shadowColor,
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: dark ? 0.7 : 0.28,
      shadowRadius: 16,
      elevation: 6,
    },
  };
}
