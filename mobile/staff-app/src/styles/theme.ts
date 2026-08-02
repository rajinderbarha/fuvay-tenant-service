import { StyleSheet } from "react-native";

// UX-05 Round 5: dark palette added. Pattern mirrors
// frontend/packages/design-system's ThemeProvider (preference: light|dark|
// system -> resolvedTheme, persisted, system-driven via a platform API) --
// see src/context/ThemeContext.tsx for the RN equivalent (Appearance API +
// AsyncStorage instead of matchMedia + localStorage). This file stays the
// SOURCE OF TRUTH for both palettes; ThemeContext only resolves which one
// is active.
// Warm-orange palette — matches frontend/super-admin and frontend/tenant-portal's
// globals.css exactly (brand #F2994A / accent #FFB45C), the canonical ServiceOS
// design system. Previously this file used an unrelated navy-blue palette,
// making the technician app visually inconsistent with every other ServiceOS app.
export const lightColors = {
  brand:"#F2994A", brandLight:"#FFB45C", accent:"#FFB45C", accentLight:"#FFF4E6",
  bg:"#F7F7F5", surface:"#FFFFFF", surfaceSunken:"#FBFAF8",
  border:"#E7E4DD", borderStrong:"#D4CFC4",
  textPrimary:"#221D14", textSecondary:"#6B6153", textTertiary:"#A39A8A",
  textInverse:"#FFFFFF", textLink:"#E0812F",
  success:"#16A34A", successBg:"#F0FDF4", successBorder:"#BBF7D0", successText:"#15803D",
  warning:"#D97706", warningBg:"#FFFBEB", warningBorder:"#FDE68A", warningText:"#B45309",
  danger:"#DC2626",  dangerBg:"#FEF2F2",  dangerBorder:"#FECACA",  dangerText:"#B91C1C",
  info:"#6B6153",    infoBg:"#F3F1EA",    infoBorder:"#D4CFC4",    infoText:"#45402F",
  tabActive:"#F2994A", tabInactive:"#A39A8A", tabBg:"#FFFFFF",
} as const;

// Dark palette: same keys as lightColors (enforced by DarkColors type
// below), inverted surfaces/text, desaturated-but-legible accent/status
// colors chosen for reasonable contrast against a dark surface -- not a
// pixel-audited dark-mode design pass (no contrast-ratio tool was run;
// see light-dark-theme-report.md for the honest scope of this work).
export const darkColors: Record<keyof typeof lightColors, string> = {
  brand:"#F2994A", brandLight:"#FFB45C", accent:"#FFB45C", accentLight:"#3A2A0A",
  bg:"#171614", surface:"#201E1B", surfaceSunken:"#171614",
  border:"#38352F", borderStrong:"#4A463E",
  textPrimary:"#F5F3EF", textSecondary:"#C9C3B7", textTertiary:"#8A8375",
  textInverse:"#171614", textLink:"#FFB45C",
  success:"#4ADE80", successBg:"#0F2A1A", successBorder:"#1F5C36", successText:"#86EFAC",
  warning:"#FBBF24", warningBg:"#3A2A0A", warningBorder:"#7A5A16", warningText:"#FDE68A",
  danger:"#F87171",  dangerBg:"#3A1414",  dangerBorder:"#7A2A2A",  dangerText:"#FCA5A5",
  info:"#C9C3B7",    infoBg:"#2A2724",    infoBorder:"#4A463E",    infoText:"#E4E0D8",
  tabActive:"#F2994A", tabInactive:"#8A8375", tabBg:"#201E1B",
};

export type ColorScheme = "light" | "dark";
export function getColors(scheme: ColorScheme) {
  return scheme === "dark" ? darkColors : lightColors;
}

export const theme = {
  colors: lightColors,
  spacing: { xs:4, sm:8, md:12, base:16, lg:20, xl:24, xxl:32, xxxl:48 },
  font: {
    size: { xs:11, sm:12, base:14, md:15, lg:16, xl:18, xxl:20, xxxl:24, huge:30 },
    weight: { regular:"400" as const, medium:"500" as const, semibold:"600" as const,
              bold:"700" as const, extrabold:"800" as const },
  },
  radius: { sm:4, md:8, lg:12, xl:16, full:999 },
  shadow: {
    sm: { shadowColor:"#000", shadowOffset:{width:0,height:1}, shadowOpacity:0.06, shadowRadius:3, elevation:2 },
    md: { shadowColor:"#000", shadowOffset:{width:0,height:4}, shadowOpacity:0.10, shadowRadius:8, elevation:4 },
    lg: { shadowColor:"#000", shadowOffset:{width:0,height:8}, shadowOpacity:0.14, shadowRadius:16, elevation:8 },
  },
} as const;

export const gs = StyleSheet.create({
  screen:    { flex:1, backgroundColor:theme.colors.bg },
  container: { flex:1, paddingHorizontal:theme.spacing.base },
  card:      { backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
               padding:theme.spacing.base, ...theme.shadow.sm },
  row:       { flexDirection:"row", alignItems:"center" },
  label:     { fontSize:theme.font.size.sm, fontWeight:theme.font.weight.bold,
               color:theme.colors.textTertiary, textTransform:"uppercase", letterSpacing:0.8 },
  sep:       { height:1, backgroundColor:theme.colors.border },
});
