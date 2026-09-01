import React from "react";
import type { StyleProp, ViewStyle } from "react-native";
import { View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Defs, RadialGradient, Rect, Stop } from "react-native-svg";

import { useTheme } from "../../design-system/theme";

export interface FuvayTileProps {
  children: React.ReactNode;
  style: StyleProp<ViewStyle>;
  borderRadius: number;
  inset?: number;
}

/** Shared reference tile face for Home, controls and the centre AI tab. */
export function FuvayTile({ children, style, borderRadius, inset = 6 }: FuvayTileProps) {
  const { theme } = useTheme();
  const tile = theme.fuvay.tile;
  const offsets = ["0%", "70%", "84%", "92%", "97%", "100%"];
  return (
    <View style={[{ position: "relative", borderRadius, shadowColor: tile.outerShadow.color, shadowOffset: { width: 0, height: tile.outerShadow.offsetY }, shadowRadius: tile.outerShadow.radius, shadowOpacity: tile.outerShadow.opacity }, style]}>
      {/* Clip in React Native dp space. Android SVG `rx` is resolved in the
          SVG viewport's physical units; at 440dpi an 82dp circle was clipped
          with a 41px radius and therefore appeared as a rounded square. */}
      <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, right: 0, bottom: 0, borderRadius, overflow: "hidden" }}>
        <Svg width="100%" height="100%" style={{ position: "absolute", left: 0, top: 0 }}>
          <Defs>
            {/* CSS `radial-gradient(circle at 50% 50%, ...)` sizes the circle
                to the farthest corner: sqrt(2)/2 (70.7107%) for a square. */}
            <RadialGradient id="fuvayTileOuter" cx="50%" cy="50%" r="70.7107%">
              {tile.outerStops.map((color, index) => <Stop key={`${offsets[index]}-${color}`} offset={offsets[index]} stopColor={color} />)}
            </RadialGradient>
          </Defs>
          <Rect width="100%" height="100%" fill="url(#fuvayTileOuter)" />
        </Svg>
      </View>
      <LinearGradient colors={tile.innerStops as [string, string, ...string[]]} locations={[0, 0.4, 0.75, 1]} style={{ position: "absolute", left: inset, top: inset, right: inset, bottom: inset, borderRadius: Math.max(1, borderRadius - inset), borderWidth: 1, borderColor: tile.innerHairline, alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
        <View pointerEvents="none" style={{ position: "absolute", left: 2, top: 0, right: 2, height: 1, backgroundColor: tile.innerHighlight }} />
        {children}
      </LinearGradient>
    </View>
  );
}
