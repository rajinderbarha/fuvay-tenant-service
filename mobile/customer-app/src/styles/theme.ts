import { StyleSheet } from "react-native";

// UX-07 Round 4 Pass 2: added a real dark palette alongside the existing
// light palette. Both share the exact same key set so any code still
// importing the static `theme` export (light, pre-dark-mode default)
// continues to compile and render unchanged, while code migrated to
// `useTheme()` (see src/context/ThemeContext.tsx) gets the active palette
// for the user's System/Light/Dark selection.
const lightColors = {
  // Customer brand — warmer, more consumer-friendly than staff app
  brand:        "#1E3A5F",
  brandLight:   "#4A90D9",
  accent:       "#2E86AB",
  accentWarm:   "#F59E0B",
  accentLight:  "#EBF6FB",
  // Surfaces
  bg:           "#F8FAFF",
  surface:      "#FFFFFF",
  surfaceSunken:"#F1F5F9",
  surfaceCard:  "#FFFFFF",
  surfaceRaised:"#FFFFFF",
  surfaceInteractive:"#F1F5F9",
  surfaceSelected:"#EBF6FB",
  surfaceDisabled:"#F1F5F9",
  border:       "#E2E8F0",
  borderStrong: "#CBD5E1",
  // Text
  textPrimary:  "#0F172A",
  textSecondary:"#475569",
  textTertiary: "#94A3B8",
  textInverse:  "#FFFFFF",
  textDisabled: "#CBD5E1",
  textLink:     "#2E86AB",
  // Semantic
  success:      "#16A34A", successBg:"#F0FDF4", successText:"#15803D", successBorder:"#BBF7D0",
  warning:      "#D97706", warningBg:"#FFFBEB", warningText:"#B45309", warningBorder:"#FDE68A",
  danger:       "#DC2626", dangerBg: "#FEF2F2", dangerText: "#B91C1C", dangerBorder: "#FECACA",
  info:         "#0EA5E9", infoBg:   "#F0F9FF", infoText:   "#0369A1", infoBorder:   "#BAE6FD",
  // Star rating
  star:         "#F59E0B",
  starEmpty:    "#E2E8F0",
  // UX-06 Round 3 fix: TabNavigator.tsx referenced these two tokens (a
  // pre-existing typecheck error, Pattern D in typecheck-error-
  // classification.md) but they were never defined.
  tabActive:    "#1E3A5F",
  tabInactive:  "#94A3B8",
  // Chat bubbles (SmartBot / DeepSeekChatScreen)
  bubbleCustomer:     "#1E3A5F",
  bubbleCustomerText: "#FFFFFF",
  bubbleAssistant:    "#FFFFFF",
  bubbleAssistantText:"#0F172A",
  bubbleSystem:       "#F1F5F9",
  bubbleSystemText:   "#475569",
  bubbleError:        "#FEF2F2",
  bubbleErrorText:    "#B91C1C",
  statusBarStyle:     "dark" as "dark" | "light",
  overlay:            "rgba(15,23,42,0.45)",
};

const darkColors: typeof lightColors = {
  brand:        "#4A90D9",
  brandLight:   "#7CB4E8",
  accent:       "#5FB4D9",
  accentWarm:   "#FBBF24",
  accentLight:  "#16324A",
  // Surfaces — layered hierarchy, not pure black
  bg:           "#0B1220",
  surface:      "#131B2C",
  surfaceSunken:"#0F1727",
  surfaceCard:  "#161F33",
  surfaceRaised:"#1C2740",
  surfaceInteractive:"#1E2A44",
  surfaceSelected:"#1E3A5F",
  surfaceDisabled:"#131B2C",
  border:       "#26324A",
  borderStrong: "#374761",
  // Text
  textPrimary:  "#F1F5F9",
  textSecondary:"#B8C4D9",
  textTertiary: "#7E8CA8",
  textInverse:  "#0F172A",
  textDisabled: "#4B5670",
  textLink:     "#7CC7EA",
  // Semantic (kept legible on dark surfaces)
  success:      "#4ADE80", successBg:"#123420", successText:"#86EFAC", successBorder:"#1F5A38",
  warning:      "#FBBF24", warningBg:"#3A2B0A", warningText:"#FCD34D", warningBorder:"#5C4413",
  danger:       "#F87171", dangerBg: "#3A1414", dangerText: "#FCA5A5", dangerBorder:"#5C1F1F",
  info:         "#38BDF8", infoBg:   "#0C2A3A", infoText:   "#7DD3FC", infoBorder:  "#164E63",
  // Star rating
  star:         "#FBBF24",
  starEmpty:    "#374761",
  tabActive:    "#7CC7EA",
  tabInactive:  "#5C6B8A",
  bubbleCustomer:     "#2E5D8C",
  bubbleCustomerText: "#F1F5F9",
  bubbleAssistant:    "#1C2740",
  bubbleAssistantText:"#F1F5F9",
  bubbleSystem:       "#161F33",
  bubbleSystemText:   "#B8C4D9",
  bubbleError:        "#3A1414",
  bubbleErrorText:    "#FCA5A5",
  statusBarStyle:     "light" as "dark" | "light",
  overlay:            "rgba(0,0,0,0.6)",
};

const shared = {
  spacing: { xs:4, sm:8, md:12, base:16, lg:20, xl:24, xxl:32, xxxl:48 },
  font: {
    size: { xs:11, sm:12, base:14, md:15, lg:16, xl:18, xxl:20, xxxl:24, huge:32 },
    weight: { regular:"400" as const, medium:"500" as const,
              semibold:"600" as const, bold:"700" as const, extrabold:"800" as const },
  },
  radius: { sm:6, md:10, lg:16, xl:22, full:999 },
};

export function buildTheme(mode: "light" | "dark") {
  const colors = mode === "dark" ? darkColors : lightColors;
  return {
    mode,
    colors,
    ...shared,
    shadow: {
      sm: { shadowColor: mode === "dark" ? "#000000" : "#1E3A5F", shadowOffset:{width:0,height:2}, shadowOpacity: mode === "dark" ? 0.3 : 0.06, shadowRadius:6, elevation:2 },
      md: { shadowColor: mode === "dark" ? "#000000" : "#1E3A5F", shadowOffset:{width:0,height:4}, shadowOpacity: mode === "dark" ? 0.4 : 0.10, shadowRadius:12, elevation:5 },
      lg: { shadowColor: mode === "dark" ? "#000000" : "#1E3A5F", shadowOffset:{width:0,height:8}, shadowOpacity: mode === "dark" ? 0.5 : 0.15, shadowRadius:20, elevation:10 },
    },
  } as const;
}

export type Theme = ReturnType<typeof buildTheme>;

// Backward-compat static export (light palette) -- unmigrated screens that
// still `import { theme }` directly keep rendering exactly as before.
export const theme = buildTheme("light");

export const gs = StyleSheet.create({
  screen:    { flex:1, backgroundColor:theme.colors.bg },
  container: { flex:1, paddingHorizontal:theme.spacing.base },
  card:      { backgroundColor:theme.colors.surface, borderRadius:theme.radius.lg,
               padding:theme.spacing.base, ...theme.shadow.sm },
  row:       { flexDirection:"row", alignItems:"center" },
  label:     { fontSize:theme.font.size.xs, fontWeight:theme.font.weight.bold,
               color:theme.colors.textTertiary, textTransform:"uppercase", letterSpacing:1 },
  sep:       { height:1, backgroundColor:theme.colors.border },
  sectionTitle:{ fontSize:theme.font.size.lg, fontWeight:theme.font.weight.bold,
                 color:theme.colors.textPrimary },
});
