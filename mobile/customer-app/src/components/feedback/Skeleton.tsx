import React, { useEffect, useRef, useState } from "react";
import { Animated, AccessibilityInfo, type ViewStyle } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import { duration } from "../../design-system/tokens/motion";

export interface SkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  radius?: number;
  style?: ViewStyle;
}

/** A single skeleton block. Compose several to build skeleton layouts. */
export function Skeleton({ width = "100%", height = 16, radius, style }: SkeletonProps) {
  const { theme } = useAppTheme();
  const opacity = useRef(new Animated.Value(0.6)).current;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled?.()
      .then(setReduceMotion)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: duration.slow, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.6, duration: duration.slow, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [opacity, reduceMotion]);

  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[
        {
          width,
          height,
          borderRadius: radius ?? theme.radii.sm,
          backgroundColor: theme.colors.skeletonBase,
          opacity: reduceMotion ? 0.75 : opacity,
        },
        style,
      ]}
    />
  );
}
