import React, { useEffect, useRef } from "react";
import { Animated, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

export function Skeleton({ width="100%", height, radius=theme.radius.md, style }:
  { width?:number|"100%"; height:number; radius?:number; style?:ViewStyle }) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.loop(Animated.sequence([
      Animated.timing(anim,{ toValue:1, duration:700, useNativeDriver:true }),
      Animated.timing(anim,{ toValue:0, duration:700, useNativeDriver:true }),
    ])).start();
  },[anim]);
  return <Animated.View style={[{ width, height, borderRadius:radius,
    backgroundColor:theme.colors.border, opacity:anim.interpolate({inputRange:[0,1],outputRange:[0.4,0.85]}) }, style]} />;
}
