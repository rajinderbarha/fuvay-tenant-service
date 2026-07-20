import { StyleSheet } from "react-native";

// UX-05 Round 5: dark palette added. Pattern mirrors
// frontend/packages/design-system's ThemeProvider (preference: light|dark|
// system -> resolvedTheme, persisted, system-driven via a platform API) --
// see src/context/ThemeContext.tsx for the RN equivalent (Appearance API +
// AsyncStorage instead of matchMedia + localStorage). This file stays the
// SOURCE OF TRUTH for both palettes; ThemeContext only resolves which one
// is active.
export const lightColors = {
  brand:"#1E3A5F", brandLight:"#4A90D9", accent:"#2E86AB", accentLight:"#EBF6FB",
  bg:"#F0F4F8", surface:"#FFFFFF", surfaceSunken:"#F5F7FA",
  border:"#E2E8F0", borderStrong:"#CBD5E1",
  textPrimary:"#0F172A", textSecondary:"#475569", textTertiary:"#94A3B8",
  textInverse:"#FFFFFF", textLink:"#2E86AB",
  success:"#16A34A", successBg:"#F0FDF4", successBorder:"#BBF7D0", successText:"#15803D",
  warning:"#D97706", warningBg:"#FFFBEB", warningBorder:"#FDE68A", warningText:"#B45309",
  danger:"#DC2626",  dangerBg:"#FEF2F2",  dangerBorder:"#FECACA",  dangerText:"#B91C1C",
  info:"#0EA5E9",    infoBg:"#F0F9FF",    infoBorder:"#BAE6FD",    infoText:"#0369A1",
  tabActive:"#1E3A5F", tabInactive:"#94A3B8", tabBg:"#FFFFFF",
} as const;

// Dark palette: same keys as lightColors (enforced by DarkColors type
// below), inverted surfaces/text, desaturated-but-legible accent/status
// colors chosen for reasonable contrast against a dark surface -- not a
// pixel-audited dark-mode design pass (no contrast-ratio tool was run;
// see light-dark-theme-report.md for the honest scope of this work).
export const darkColors: Record<keyof typeof lightColors, string> = {
  brand:"#4A90D9", brandLight:"#7CB4E8", accent:"#5EB3D6", accentLight:"#1B3A47",
  bg:"#0B1220", surface:"#161E2E", surfaceSunken:"#1E2838",
  border:"#2A3547", borderStrong:"#3C4A61",
  textPrimary:"#F1F5F9", textSecondary:"#B6C2D1", textTertiary:"#7C8AA0",
  textInverse:"#0F172A", textLink:"#7CC5E8",
  success:"#4ADE80", successBg:"#0F2A1A", successBorder:"#1F5C36", successText:"#86EFAC",
  warning:"#FBBF24", warningBg:"#3A2A0A", warningBorder:"#7A5A16", warningText:"#FDE68A",
  danger:"#F87171",  dangerBg:"#3A1414",  dangerBorder:"#7A2A2A",  dangerText:"#FCA5A5",
  info:"#38BDF8",    infoBg:"#0E2A3A",    infoBorder:"#1E5A7A",    infoText:"#7DD3FC",
  tabActive:"#4A90D9", tabInactive:"#7C8AA0", tabBg:"#161E2E",
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
