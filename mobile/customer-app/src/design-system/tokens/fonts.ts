import { Platform } from "react-native";

/**
 * Fuvay v2 font families.
 *
 * ── The weight caveat that shapes this whole file ─────────────────────────
 * With custom TTFs on React Native, `fontWeight` does NOT select a weight —
 * each weight is a SEPARATE registered family. Setting
 * `fontFamily: "Barlow_400Regular"` with `fontWeight: "600"` gives you
 * regular Barlow on iOS and, on some Android builds, a synthetically
 * smeared fake-bold. So the type scale in ./typography.ts pairs every style
 * with the correctly weighted family name, and `fontWeight` is kept
 * alongside only as a hint for the system-font fallback below.
 *
 * ── Fallback ──────────────────────────────────────────────────────────────
 * `useFuvayFonts()` reports when the TTFs are ready, but the tree may render
 * a frame before that (and unit tests never load fonts at all). React Native
 * silently falls back to the system font for an unregistered family, so text
 * still renders — it is simply not Barlow for that frame. Nothing here
 * throws or blocks on a missing font.
 */

/** Family names exactly as registered by useFuvayFonts(). */
export const fuvayFontFamily = {
  regular: "Barlow_400Regular",
  medium: "Barlow_500Medium",
  semibold: "Barlow_600SemiBold",
  bold: "Barlow_700Bold",
  /** JetBrains Mono — reserved for uppercase tracked metadata labels. */
  mono: "JetBrainsMono_400Regular",
  monoMedium: "JetBrainsMono_500Medium",
} as const;

export type FuvayFontFamily = keyof typeof fuvayFontFamily;

/**
 * System fallbacks, for anywhere that needs a concrete family string before
 * the custom fonts are registered (or on web, where the CSS stack does the
 * work). Not used by the type scale — see the caveat above.
 */
export const systemFontStack = Platform.select({
  ios: "System",
  android: "sans-serif",
  default: "Barlow, Helvetica, Arial, sans-serif",
});

export const systemMonoStack = Platform.select({
  ios: "Menlo",
  android: "monospace",
  default: "'JetBrains Mono', Menlo, monospace",
});
