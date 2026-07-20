import { StyleSheet } from "react-native";

export const theme = {
  colors: {
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
    border:       "#E2E8F0",
    borderStrong: "#CBD5E1",
    // Text
    textPrimary:  "#0F172A",
    textSecondary:"#475569",
    textTertiary: "#94A3B8",
    textInverse:  "#FFFFFF",
    textLink:     "#2E86AB",
    // Semantic
    success:      "#16A34A", successBg:"#F0FDF4", successText:"#15803D", successBorder:"#BBF7D0",
    warning:      "#D97706", warningBg:"#FFFBEB", warningText:"#B45309", warningBorder:"#FDE68A",
    danger:       "#DC2626", dangerBg: "#FEF2F2", dangerText: "#B91C1C", dangerBorder: "#FECACA",
    info:         "#0EA5E9", infoBg:   "#F0F9FF", infoText:   "#0369A1", infoBorder:   "#BAE6FD",
    // Tab bar (referenced by TabNavigator; additive — not previously defined)
    tabActive:    "#1E3A5F",
    tabInactive:  "#94A3B8",
    // Star rating
    star:         "#F59E0B",
    starEmpty:    "#E2E8F0",
  },
  spacing: { xs:4, sm:8, md:12, base:16, lg:20, xl:24, xxl:32, xxxl:48 },
  font: {
    size: { xs:11, sm:12, base:14, md:15, lg:16, xl:18, xxl:20, xxxl:24, huge:32 },
    weight: { regular:"400" as const, medium:"500" as const,
              semibold:"600" as const, bold:"700" as const, extrabold:"800" as const },
  },
  radius: { sm:6, md:10, lg:16, xl:22, full:999 },
  shadow: {
    sm: { shadowColor:"#1E3A5F", shadowOffset:{width:0,height:2}, shadowOpacity:0.06, shadowRadius:6, elevation:2 },
    md: { shadowColor:"#1E3A5F", shadowOffset:{width:0,height:4}, shadowOpacity:0.10, shadowRadius:12, elevation:5 },
    lg: { shadowColor:"#1E3A5F", shadowOffset:{width:0,height:8}, shadowOpacity:0.15, shadowRadius:20, elevation:10 },
  },
} as const;

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
