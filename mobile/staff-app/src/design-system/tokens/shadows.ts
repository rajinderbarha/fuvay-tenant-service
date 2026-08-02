import { ViewStyle } from "react-native";

/** Elevation is subtle by design. Dark mode leans on border/surface
 * contrast rather than heavy shadow -- see buildShadows(mode) usage in
 * ../themes/buildTheme.ts. */
export function buildShadows(mode: "light" | "dark"): Record<"sm" | "md" | "lg", ViewStyle> {
  const shadowColor = mode === "dark" ? "#000000" : "#221C16";
  const opacityScale = mode === "dark" ? 1 : 0.6;
  return {
    sm: { shadowColor, shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08 * opacityScale, shadowRadius: 3, elevation: 1 },
    md: { shadowColor, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.12 * opacityScale, shadowRadius: 6, elevation: 3 },
    lg: { shadowColor, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.16 * opacityScale, shadowRadius: 12, elevation: 6 },
  };
}
