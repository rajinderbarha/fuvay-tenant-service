import React from "react";
import { ActivityIndicator, Text, TouchableOpacity, type ViewStyle } from "react-native";
import { useTheme } from "../context/ThemeContext";
import type { Theme } from "../styles/theme";

type Variant = "primary"|"secondary"|"outline"|"ghost"|"danger";
type Size    = "sm"|"md"|"lg";

interface Props {
  label:string; onPress?:()=>void; variant?:Variant; size?:Size;
  loading?:boolean; disabled?:boolean; fullWidth?:boolean; style?:ViewStyle;
  accessibilityLabel?:string;
}

function variantStyles(theme: Theme): Record<Variant,{bg:string;text:string;border:string}> {
  return {
    primary:  { bg:theme.colors.brand,      text:theme.colors.textInverse, border:"transparent" },
    secondary:{ bg:theme.colors.surface,    text:theme.colors.textPrimary, border:theme.colors.border },
    outline:  { bg:"transparent",           text:theme.colors.brand,       border:theme.colors.brand },
    ghost:    { bg:"transparent",           text:theme.colors.textSecondary,border:"transparent" },
    danger:   { bg:theme.colors.dangerBg,   text:theme.colors.dangerText,  border:theme.colors.dangerBorder },
  };
}
function sizeStyles(theme: Theme): Record<Size,{h:number;px:number;fs:number;r:number}> {
  return {
    sm:{ h:36, px:14, fs:theme.font.size.sm,  r:theme.radius.md },
    md:{ h:46, px:20, fs:theme.font.size.base, r:theme.radius.lg },
    lg:{ h:54, px:24, fs:theme.font.size.lg,  r:theme.radius.lg },
  };
}

// UX-07 Round 4 Pass 2: migrated off the static `theme` import onto
// `useTheme()` so every screen using <Button/> automatically renders
// correctly in dark mode. Added accessibilityRole/State/Label (button
// role, disabled announcement, explicit label override for icon-only
// callers) and a minimum 44px tap target regardless of visual size.
export function Button({ label, onPress, variant="primary", size="md", loading, disabled, fullWidth, style, accessibilityLabel }:Props) {
  const { theme } = useTheme();
  const VS = variantStyles(theme); const SS = sizeStyles(theme);
  const v=VS[variant]; const s=SS[size]; const dis=disabled||loading;
  return (
    <TouchableOpacity onPress={onPress} disabled={dis} activeOpacity={0.78}
      accessible accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: !!dis, busy: !!loading }}
      hitSlop={{ top:8, bottom:8, left:8, right:8 }}
      style={[{height:Math.max(s.h,44),paddingHorizontal:s.px,borderRadius:s.r,borderWidth:1,
        backgroundColor:v.bg, borderColor:v.border, opacity:dis?0.55:1,
        alignItems:"center",justifyContent:"center",flexDirection:"row",
        width:fullWidth?"100%":undefined},style]}>
      {loading ? <ActivityIndicator size="small" color={v.text}/>
               : <Text style={{color:v.text,fontSize:s.fs,fontWeight:"700"}}>{label}</Text>}
    </TouchableOpacity>
  );
}
