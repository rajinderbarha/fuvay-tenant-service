import React, { useEffect, useRef, useState } from "react";
import { AccessibilityInfo, Animated, type ViewStyle } from "react-native";
import { useTheme } from "../context/ThemeContext";

// UX-07 Round 4 Pass 2: migrated to useTheme() for dark-mode surface color,
// and now respects the platform "Reduce Motion" accessibility setting by
// holding a static mid-opacity fill instead of looping the pulse animation
// (the loading-state semantics are preserved via accessibilityLabel; only
// the animation itself is skipped).
export function Skeleton({ width="100%", height, radius, style }:
  { width?:number|"100%"; height:number; radius?:number; style?:ViewStyle }) {
  const { theme } = useTheme();
  const anim = useRef(new Animated.Value(0)).current;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled?.().then(v => { if (mounted) setReduceMotion(!!v); }).catch(() => {});
    const sub = AccessibilityInfo.addEventListener?.("reduceMotionChanged", (v: boolean) => setReduceMotion(!!v));
    return () => { mounted = false; sub?.remove?.(); };
  }, []);

  useEffect(() => {
    if (reduceMotion) { anim.setValue(0.6); return; }
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(anim,{ toValue:1, duration:700, useNativeDriver:true }),
      Animated.timing(anim,{ toValue:0, duration:700, useNativeDriver:true }),
    ]));
    loop.start();
    return () => loop.stop();
  },[anim, reduceMotion]);

  return <Animated.View accessible accessibilityLabel="Loading"
    style={[{ width, height, borderRadius:radius ?? theme.radius.md,
    backgroundColor:theme.colors.border,
    opacity: reduceMotion ? 0.6 : anim.interpolate({inputRange:[0,1],outputRange:[0.4,0.85]}) }, style]} />;
}
