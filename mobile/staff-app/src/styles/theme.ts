import { StyleSheet } from "react-native";

export const theme = {
  colors: {
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
  },
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
