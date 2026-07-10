import React from "react";
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

type Variant = "primary"|"secondary"|"outline"|"ghost"|"danger";
type Size    = "sm"|"md"|"lg";

interface Props {
  label:string; onPress?:()=>void; variant?:Variant; size?:Size;
  loading?:boolean; disabled?:boolean; fullWidth?:boolean; style?:ViewStyle;
}

const VS: Record<Variant,{bg:string;text:string;border:string}> = {
  primary:  { bg:theme.colors.brand,      text:theme.colors.textInverse, border:"transparent" },
  secondary:{ bg:theme.colors.surface,    text:theme.colors.textPrimary, border:theme.colors.border },
  outline:  { bg:"transparent",           text:theme.colors.brand,       border:theme.colors.brand },
  ghost:    { bg:"transparent",           text:theme.colors.textSecondary,border:"transparent" },
  danger:   { bg:theme.colors.dangerBg,   text:theme.colors.dangerText,  border:theme.colors.dangerBorder },
};
const SS: Record<Size,{h:number;px:number;fs:number;r:number}> = {
  sm:{ h:36, px:14, fs:theme.font.size.sm,  r:theme.radius.md },
  md:{ h:46, px:20, fs:theme.font.size.base, r:theme.radius.lg },
  lg:{ h:54, px:24, fs:theme.font.size.lg,  r:theme.radius.lg },
};
export function Button({ label, onPress, variant="primary", size="md", loading, disabled, fullWidth, style }:Props) {
  const v=VS[variant]; const s=SS[size]; const dis=disabled||loading;
  return (
    <TouchableOpacity onPress={onPress} disabled={dis} activeOpacity={0.78}
      style={[{height:s.h,paddingHorizontal:s.px,borderRadius:s.r,borderWidth:1,
        backgroundColor:v.bg, borderColor:v.border, opacity:dis?0.55:1,
        alignItems:"center",justifyContent:"center",flexDirection:"row",
        width:fullWidth?"100%":undefined},style]}>
      {loading ? <ActivityIndicator size="small" color={v.text}/>
               : <Text style={{color:v.text,fontSize:s.fs,fontWeight:"700"}}>{label}</Text>}
    </TouchableOpacity>
  );
}
