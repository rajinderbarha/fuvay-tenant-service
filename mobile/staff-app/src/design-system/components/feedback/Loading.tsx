import React, { useEffect, useRef } from "react";
import { ActivityIndicator, Animated, View, Easing } from "react-native";
import { useTheme, useReducedMotion } from "../../themes";

export function LoadingSpinner({ size = "small", color }: { size?: "small" | "large"; color?: string }) {
  const { theme } = useTheme();
  return <ActivityIndicator size={size} color={color ?? theme.colors.brandPrimary} accessibilityLabel="Loading" />;
}

export interface SkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  radius?: number;
}

/** Skeleton -- shimmering placeholder block. Respects reduced-motion (falls
 * back to a static translucent block instead of animating). */
export function Skeleton({ width = "100%", height = 16, radius }: SkeletonProps) {
  const { theme } = useTheme();
  const reduceMotion = useReducedMotion();
  const opacity = useRef(new Animated.Value(theme.opacity.skeleton)).current;

  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.24, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(opacity, { toValue: theme.opacity.skeleton, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity, reduceMotion, theme.opacity.skeleton]);

  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={{
        width, height, borderRadius: radius ?? theme.radius.radiusSmall,
        backgroundColor: theme.colors.textPrimary,
        opacity: reduceMotion ? theme.opacity.skeleton : opacity,
      }}
    />
  );
}

export interface ProgressBarProps {
  progress: number; // 0-1
  tone?: "brand" | "success" | "danger";
}

export function ProgressBar({ progress, tone = "brand" }: ProgressBarProps) {
  const { theme } = useTheme();
  const clamped = Math.max(0, Math.min(1, progress));
  const color = tone === "success" ? theme.colors.statusSuccess : tone === "danger" ? theme.colors.statusDanger : theme.colors.brandPrimary;

  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(clamped * 100) }}
      style={{ height: 6, borderRadius: theme.radius.radiusPill, backgroundColor: theme.colors.backgroundSunken, overflow: "hidden" }}
    >
      <View style={{ width: `${clamped * 100}%`, height: "100%", backgroundColor: color }} />
    </View>
  );
}
