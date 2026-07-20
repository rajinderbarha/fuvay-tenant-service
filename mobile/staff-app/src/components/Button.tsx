import React from "react";
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

type Variant = "primary"|"secondary"|"outline"|"ghost"|"danger"|"success";
type Size    = "sm"|"md"|"lg";

interface Props {
  label:    string;
  onPress?: () => void;
  variant?: Variant;
  size?:    Size;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
}

const VS: Record<Variant, { bg:string; text:string; border:string }> = {
  primary:  { bg:theme.colors.brand,       text:theme.colors.textInverse, border:"transparent" },
  secondary:{ bg:theme.colors.surface,     text:theme.colors.textPrimary, border:theme.colors.border },
  outline:  { bg:"transparent",            text:theme.colors.brand,       border:theme.colors.brand },
  ghost:    { bg:"transparent",            text:theme.colors.textSecondary,border:"transparent" },
  danger:   { bg:theme.colors.dangerBg,    text:theme.colors.dangerText,  border:theme.colors.dangerBorder },
  success:  { bg:theme.colors.successBg,   text:theme.colors.successText, border:theme.colors.successBorder },
};

// UX-05 Round 4 a11y pass: "sm" was 36pt tall, below the 44x44pt minimum
// touch-target guideline -- bumped to 44 so every Button size meets it.
const SS: Record<Size, { height:number; px:number; fontSize:number; radius:number }> = {
  sm: { height:44, px:14, fontSize:theme.font.size.sm, radius:theme.radius.md },
  md: { height:44, px:20, fontSize:theme.font.size.base, radius:theme.radius.lg },
  lg: { height:54, px:24, fontSize:theme.font.size.lg, radius:theme.radius.lg },
};

export function Button({ label, onPress, variant="primary", size="md", loading, disabled, fullWidth, style }: Props) {
  const v = VS[variant]; const sz = SS[size];
  const isDisabled = disabled || loading;
  return (
    <TouchableOpacity
      onPress={onPress} disabled={isDisabled} activeOpacity={0.75}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: isDisabled, busy: !!loading }}
      style={[s.base, { backgroundColor:v.bg, borderColor:v.border, borderRadius:sz.radius,
        height:sz.height, paddingHorizontal:sz.px, opacity:isDisabled?0.55:1,
        width:fullWidth?"100%":undefined }, style]}>
      {loading
        ? <ActivityIndicator size="small" color={v.text} />
        : <Text style={[s.label, { color:v.text, fontSize:sz.fontSize }]}>{label}</Text>}
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  base:  { borderWidth:1, alignItems:"center", justifyContent:"center", flexDirection:"row" },
  label: { fontWeight:"600" },
});
