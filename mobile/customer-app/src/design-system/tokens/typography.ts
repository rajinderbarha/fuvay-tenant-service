import { Platform } from "react-native";

/**
 * Platform-safe font family. Falls back to the OS default sans-serif when a
 * custom font has not been loaded, so text never disappears on font-load failure.
 */
const fontFamily = Platform.select({ ios: "System", android: "sans-serif", default: "System" });
const fontFamilyMedium = Platform.select({ ios: "System", android: "sans-serif-medium", default: "System" });

export interface TypographyStyle {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  fontWeight: "400" | "500" | "600" | "700" | "800";
  letterSpacing?: number;
}

// lineHeight is intentionally generous (>=1.25x fontSize) so scaled/large
// accessibility text does not clip. Containers using these styles must not
// impose a fixed height.
export const typography: Record<string, TypographyStyle> = {
  displayLarge: { fontFamily: fontFamily!, fontSize: 34, lineHeight: 42, fontWeight: "800" },
  displayMedium: { fontFamily: fontFamily!, fontSize: 28, lineHeight: 36, fontWeight: "800" },
  headingLarge: { fontFamily: fontFamily!, fontSize: 24, lineHeight: 32, fontWeight: "700" },
  headingMedium: { fontFamily: fontFamily!, fontSize: 20, lineHeight: 28, fontWeight: "700" },
  headingSmall: { fontFamily: fontFamily!, fontSize: 18, lineHeight: 26, fontWeight: "700" },
  titleLarge: { fontFamily: fontFamilyMedium!, fontSize: 17, lineHeight: 24, fontWeight: "600" },
  titleMedium: { fontFamily: fontFamilyMedium!, fontSize: 15, lineHeight: 22, fontWeight: "600" },
  titleSmall: { fontFamily: fontFamilyMedium!, fontSize: 13, lineHeight: 20, fontWeight: "600" },
  bodyLarge: { fontFamily: fontFamily!, fontSize: 16, lineHeight: 24, fontWeight: "400" },
  bodyMedium: { fontFamily: fontFamily!, fontSize: 14, lineHeight: 21, fontWeight: "400" },
  bodySmall: { fontFamily: fontFamily!, fontSize: 13, lineHeight: 19, fontWeight: "400" },
  labelLarge: { fontFamily: fontFamilyMedium!, fontSize: 14, lineHeight: 20, fontWeight: "600" },
  labelMedium: { fontFamily: fontFamilyMedium!, fontSize: 12, lineHeight: 16, fontWeight: "600", letterSpacing: 0.2 },
  labelSmall: { fontFamily: fontFamilyMedium!, fontSize: 11, lineHeight: 14, fontWeight: "600", letterSpacing: 0.4 },
  caption: { fontFamily: fontFamily!, fontSize: 11, lineHeight: 15, fontWeight: "400" },
  numericEmphasis: { fontFamily: fontFamilyMedium!, fontSize: 22, lineHeight: 28, fontWeight: "700", letterSpacing: -0.2 },
};

export type TypographyVariant = keyof typeof typography;

/** Readable line length target for tablet/large screens (characters). */
export const maxReadableCharWidth = 72;
