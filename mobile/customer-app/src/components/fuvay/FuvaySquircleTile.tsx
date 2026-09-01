import React from "react";
import { Pressable, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { fuvayGradientGeometry } from "../../design-system/tokens/fuvay";
import { useTheme } from "../../design-system/theme";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppText } from "../AppText";

interface FuvaySquircleTileProps {
  icon: AppLucideName;
  label: string;
  accent: string;
  onPress: () => void;
}

/** Browse-category plate transcribed from Circle Tile Light + Dark. */
export function FuvaySquircleTile({ icon, label, accent, onPress }: FuvaySquircleTileProps) {
  const { theme } = useTheme();
  const surface = theme.fuvay.squircleTile;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Browse ${label}`}
      onPress={onPress}
      style={({ pressed }) => ({
        width: "22%",
        alignItems: "center",
        gap: 9,
        opacity: pressed ? 0.76 : 1,
        transform: [{ scale: pressed ? 0.97 : 1 }],
      })}
    >
      <LinearGradient
        colors={[...surface.stops]}
        locations={[0, 0.35, 0.7, 1]}
        start={fuvayGradientGeometry.verticalStart}
        end={fuvayGradientGeometry.verticalEnd}
        style={{
          width: "100%",
          aspectRatio: 1,
          borderRadius: 30,
          borderWidth: 1,
          borderColor: surface.hairline,
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          // iOS turns even a low-opacity neutral shadow into a broad grey
          // halo once eight tiles overlap on the light Home surface. The
          // reference light tile gets its depth from the face gradient and
          // hairline; only the dark theme needs a cast shadow.
          shadowColor: theme.fuvay.isDark ? surface.shadow.color : "transparent",
          shadowOffset: { width: 0, height: theme.fuvay.isDark ? surface.shadow.offsetY : 0 },
          shadowRadius: theme.fuvay.isDark ? surface.shadow.radius : 0,
          shadowOpacity: theme.fuvay.isDark ? surface.shadow.opacity : 0,
          // Android elevation has the same black cast, so it is dark-only too.
          elevation: theme.fuvay.isDark ? 7 : 0,
        }}
      >
        <View pointerEvents="none" style={{ position: "absolute", left: 10, right: 10, top: 0, height: 2, backgroundColor: surface.highlight }} />
        <View pointerEvents="none" style={{ position: "absolute", left: 9, right: 9, bottom: 0, height: 2, backgroundColor: surface.shade }} />
        <AppLucideIcon name={icon} size={25} color={accent} strokeWidth={1.75} />
      </LinearGradient>
      <AppText
        numberOfLines={2}
        align="center"
        variant="labelStrong"
        style={{ color: theme.fuvay.surfaces.text, fontSize: 10, lineHeight: 13 }}
      >
        {label}
      </AppText>
    </Pressable>
  );
}
