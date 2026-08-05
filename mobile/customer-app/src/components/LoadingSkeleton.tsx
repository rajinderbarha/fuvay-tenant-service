import React, { useEffect, useRef } from "react";
import { Animated, ViewStyle } from "react-native";
import { useTheme, useReducedMotion } from "../design-system/theme";

export interface LoadingSkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  radius?: number;
  style?: ViewStyle;
}

/** Shimmering placeholder block for list/card loading states. Respects
 * reduced-motion: renders a static block instead of animating when the OS
 * setting is enabled. */
export function LoadingSkeleton({ width = "100%", height = 16, radius, style }: LoadingSkeletonProps) {
  const { theme } = useTheme();
  const reduceMotion = useReducedMotion();
  const opacity = useRef(new Animated.Value(0.5)).current;

  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: theme.motion.slow, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.5, duration: theme.motion.slow, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity, reduceMotion, theme.motion.slow]);

  return (
    <Animated.View
      accessibilityElementsHidden
      style={[
        {
          width,
          height,
          borderRadius: radius ?? theme.radius.radiusSmall,
          backgroundColor: theme.colors.surfaceInteractive,
          opacity: reduceMotion ? 0.7 : opacity,
        },
        style,
      ]}
    />
  );
}
