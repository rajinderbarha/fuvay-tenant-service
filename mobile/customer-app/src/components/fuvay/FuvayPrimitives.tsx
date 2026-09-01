import React from "react";
import { Pressable, StyleProp, View, ViewStyle } from "react-native";
import Svg, { Defs, LinearGradient, RadialGradient, Rect, Stop } from "react-native-svg";

import { useTheme } from "../../design-system/theme";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppSurface } from "../AppSurface";
import { AppText } from "../AppText";

export function FuvayAmbientCanvas({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { theme } = useTheme();
  const fuvay = theme.fuvay;
  return (
    <View style={[{ flex: 1, overflow: "hidden", backgroundColor: fuvay.surfaces.shell }, style]}>
      <Svg pointerEvents="none" width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: "absolute", inset: 0 }}>
        <Defs>
          <LinearGradient id="ambientBase" x1="59" y1="0" x2="41" y2="100" gradientUnits="userSpaceOnUse">
            {fuvay.surfaces.headerGradient.map((color, index) => <Stop key={color} offset={`${index * 50}%`} stopColor={color} />)}
          </LinearGradient>
          <RadialGradient id="ambientTop" cx="84" cy="4" r="72" gradientUnits="userSpaceOnUse">
            <Stop offset="0" stopColor={fuvay.accents.a2} stopOpacity={fuvay.isDark ? 0.16 : 0.11} />
            <Stop offset="1" stopColor={fuvay.accents.a2} stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Rect width="100" height="100" fill="url(#ambientBase)" />
        <Rect width="100" height="100" fill="url(#ambientTop)" />
      </Svg>
      {children}
    </View>
  );
}

export function FuvayPanel({ children, style, inset = false }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; inset?: boolean }) {
  const { theme } = useTheme();
  return (
    <AppSurface
      variant={inset ? "inset" : "raised"}
      elevated={!inset}
      colors={inset ? theme.material.inset : [theme.fuvay.surfaces.panel, theme.fuvay.surfaces.panel]}
      style={[{ borderRadius: theme.radiusUsage.panel, padding: theme.layout.cardPadding }, style]}
    >
      {children}
    </AppSurface>
  );
}

export function FuvayEyebrow({ children, color }: { children: string; color?: string }) {
  const { theme } = useTheme();
  const accent = color ?? theme.colors.brandPrimaryStrong;
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
      <View style={{ width: theme.spacing.xl, height: 1, backgroundColor: accent }} />
      <AppText variant="metaLabelWide" style={{ color: accent }}>{children}</AppText>
    </View>
  );
}

export function FuvaySectionHeader({ title, subtitle, actionLabel, onAction }: { title: string; subtitle?: string; actionLabel?: string; onAction?: () => void }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm }}>
      <View style={{ flex: 1 }}>
        <AppText variant="headingSmall">{title}</AppText>
        {subtitle ? <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{subtitle}</AppText> : null}
      </View>
      {actionLabel && onAction ? (
        <Pressable onPress={onAction} accessibilityRole="button" accessibilityLabel={actionLabel} hitSlop={theme.spacing.sm}>
          <AppText variant="labelStrong" color="link">{actionLabel}</AppText>
        </Pressable>
      ) : null}
    </View>
  );
}

export function FuvayStatusPill({ label, tone = "info" }: { label: string; tone?: "info" | "success" | "warning" | "danger" }) {
  const { theme } = useTheme();
  const foreground = tone === "success" ? theme.colors.statusSuccess : tone === "warning" ? theme.colors.statusWarning : tone === "danger" ? theme.colors.statusDanger : theme.colors.statusInfo;
  const background = tone === "success" ? theme.colors.statusSuccessSurface : tone === "warning" ? theme.colors.statusWarningSurface : tone === "danger" ? theme.colors.statusDangerSurface : theme.colors.statusInfoSurface;
  return (
    <View style={{ minHeight: theme.metrics.control.compact, paddingHorizontal: theme.spacing.md, borderRadius: theme.radiusUsage.statusPill, backgroundColor: background, flexDirection: "row", alignItems: "center" }}>
      <AppText variant="metaLabel" style={{ color: foreground }}>{label}</AppText>
    </View>
  );
}

export function FuvayIconControl({ icon, label, onPress }: { icon: AppLucideName; label: string; onPress: () => void }) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} hitSlop={theme.spacing.sm} style={({ pressed }) => ({ opacity: pressed ? theme.opacity.pressed : 1 })}>
      <AppSurface variant="inset" elevated={false} style={{ width: theme.metrics.control.compact, height: theme.metrics.control.compact, borderRadius: theme.radius.radiusMedium, alignItems: "center", justifyContent: "center" }}>
        <AppLucideIcon name={icon} size="standard" color={theme.colors.textSecondary} />
      </AppSurface>
    </Pressable>
  );
}
