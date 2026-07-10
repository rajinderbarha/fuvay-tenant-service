import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

interface Props { width?:number|"100%"; height:number; radius?:number; style?:ViewStyle }

export function Skeleton({ width="100%", height, radius=theme.radius.md, style }: Props) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.loop(Animated.sequence([
      Animated.timing(anim, { toValue:1, duration:750, useNativeDriver:true }),
      Animated.timing(anim, { toValue:0, duration:750, useNativeDriver:true }),
    ])).start();
  }, [anim]);
  const opacity = anim.interpolate({ inputRange:[0,1], outputRange:[0.4,0.8] });
  return (
    <Animated.View style={[{ width, height, borderRadius:radius,
      backgroundColor:theme.colors.border, opacity }, style]} />
  );
}

export function SkeletonCard({ lines=3 }: { lines?:number }) {
  return (
    <View style={[{ padding:theme.spacing.base, gap:10 }]}>
      <View style={{ flexDirection:"row", justifyContent:"space-between" }}>
        <Skeleton width="50%" height={12} />
        <Skeleton width={32} height={32} radius={16} />
      </View>
      <Skeleton width="35%" height={28} />
      {Array.from({ length:lines }).map((_,i) =>
        <Skeleton key={i} width={i===lines-1?"60%":"100%"} height={12} />
      )}
    </View>
  );
}
