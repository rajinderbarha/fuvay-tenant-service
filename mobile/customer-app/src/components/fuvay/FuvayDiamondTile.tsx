import React from "react";
import { Pressable, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { useTheme } from "../../design-system/theme";
import { fuvayDiamondGeometry as geometry } from "../../design-system/tokens/fuvay";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppText } from "../AppText";

interface FuvayDiamondTileProps {
  icon: AppLucideName;
  label: string;
  accent: string;
  onPress: () => void;
}

/** Static diamond category tile from the Circle Tile Light + Dark reference.
 * The content stays upright while the two rounded plates rotate beneath it. */
export function FuvayDiamondTile({ icon, label, accent, onPress }: FuvayDiamondTileProps) {
  const { theme } = useTheme();
  const surface = theme.fuvay.diamondTile;
  const plateBase = {
    position: "absolute" as const,
    width: geometry.plateSize,
    height: geometry.plateSize,
    borderRadius: geometry.plateRadius,
    transform: [{ rotate: "45deg" }],
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Browse ${label}`}
      onPress={onPress}
      style={({ pressed }) => ({
        width: "30%",
        alignItems: "center",
        opacity: pressed ? 0.76 : 1,
        transform: [{ scale: pressed ? 0.97 : 1 }],
      })}
    >
      <View style={{ width: geometry.containerWidth, height: geometry.containerHeight }}>
        <View
          style={{
            ...plateBase,
            left: geometry.ghostLeft,
            top: geometry.ghostTop,
            padding: 1,
            backgroundColor: surface.ghostBorder,
          }}
        >
          <View style={{ flex: 1, borderRadius: geometry.plateRadius - 1, backgroundColor: surface.ghostFill }} />
        </View>

        <View
          style={{
            ...plateBase,
            left: geometry.plateLeft,
            top: geometry.plateTop,
            padding: 1,
            backgroundColor: surface.plateBorder,
            shadowColor: surface.shadow.color,
            shadowOffset: { width: 0, height: surface.shadow.offsetY },
            shadowRadius: surface.shadow.radius,
            shadowOpacity: surface.shadow.opacity,
            elevation: theme.fuvay.isDark ? 8 : 5,
          }}
        >
          <LinearGradient
            colors={[...surface.plateStops]}
            locations={[0, 0.55, 1]}
            style={{
              flex: 1,
              overflow: "hidden",
              borderRadius: geometry.plateRadius - 1,
              borderWidth: 1,
              borderColor: surface.innerHairline,
            }}
          >
            <View style={{ height: 1, marginHorizontal: 7, backgroundColor: surface.innerHighlight }} />
            <View style={{ position: "absolute", left: 7, right: 7, bottom: 0, height: 2, backgroundColor: surface.innerShade }} />
          </LinearGradient>
        </View>

        <View
          pointerEvents="none"
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: geometry.contentTop,
            height: geometry.contentHeight,
            paddingHorizontal: 19,
            alignItems: "center",
            justifyContent: "center",
            gap: geometry.contentGap,
          }}
        >
          <AppLucideIcon name={icon} size={geometry.iconSize} color={accent} strokeWidth={1.75} />
          <AppText
            numberOfLines={2}
            align="center"
            variant="labelStrong"
            style={{
              color: surface.label,
              fontSize: geometry.labelSize,
              lineHeight: geometry.labelLineHeight,
              letterSpacing: geometry.labelTracking,
              textTransform: "uppercase",
            }}
          >
            {label}
          </AppText>
        </View>
      </View>
    </Pressable>
  );
}
