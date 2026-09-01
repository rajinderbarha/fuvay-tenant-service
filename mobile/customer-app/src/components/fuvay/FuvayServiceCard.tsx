import React from "react";
import { Pressable, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { fuvayGradientGeometry } from "../../design-system/tokens/fuvay";
import { useTheme } from "../../design-system/theme";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppText } from "../AppText";

interface FuvayServiceCardProps {
  icon: AppLucideName;
  title: string;
  description: string;
  meta?: string;
  accent: string;
  actionLabel?: string;
  onPress: () => void;
}

/** Reusable coloured-corner service card from the supplied token canvas. */
export function FuvayServiceCard({
  icon,
  title,
  description,
  meta,
  accent,
  actionLabel = "BOOK",
  onPress,
}: FuvayServiceCardProps) {
  const { theme } = useTheme();
  const t = theme.fuvay;
  const surface = t.serviceCard;

  return (
    <Pressable accessibilityRole="button" accessibilityLabel={`${actionLabel} ${title}`} onPress={onPress}>
      <View
        style={{
          position: "relative",
          borderRadius: 20,
          shadowColor: surface.shadow.color,
          shadowOffset: { width: 0, height: surface.shadow.offsetY },
          shadowRadius: surface.shadow.radius,
          shadowOpacity: surface.shadow.opacity,
          elevation: t.isDark ? 6 : 0,
        }}
      >
        <LinearGradient
          colors={[...surface.stops]}
          locations={[0, 0.55, 1]}
          start={fuvayGradientGeometry.verticalStart}
          end={fuvayGradientGeometry.verticalEnd}
          style={{
            minHeight: 116,
            paddingHorizontal: 24,
            paddingVertical: 20,
            borderRadius: 20,
            borderWidth: 1,
            borderColor: surface.hairline,
            gap: 8,
          }}
        >
          <View pointerEvents="none" style={{ position: "absolute", left: 12, right: 12, top: 0, height: 1, backgroundColor: surface.highlight }} />

          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingRight: 86 }}>
            <AppLucideIcon name={icon} size={21} color={accent} strokeWidth={1.75} />
            <AppText numberOfLines={2} variant="headingSmall" style={{ color: accent, fontSize: 17, lineHeight: 20 }}>
              {title}
            </AppText>
          </View>
          <AppText numberOfLines={2} variant="bodySmall" style={{ color: t.surfaces.sub, lineHeight: 18 }}>
            {description}
          </AppText>
          {meta ? <AppText numberOfLines={1} variant="metaLabel" style={{ color: t.surfaces.faint }}>{meta}</AppText> : null}

          <View style={{ position: "absolute", right: 18, top: 14, minHeight: 38, paddingHorizontal: 16, borderRadius: 99, backgroundColor: accent, alignItems: "center", justifyContent: "center", shadowColor: surface.shadow.color, shadowOffset: { width: 0, height: 4 }, shadowRadius: 8, shadowOpacity: t.isDark ? 0.35 : 0.12, elevation: t.isDark ? 4 : 0 }}>
            <AppText variant="metaLabel" style={{ color: t.ink(accent), letterSpacing: 1.1 }}>{actionLabel}</AppText>
          </View>
        </LinearGradient>

        <View
          pointerEvents="none"
          style={{
            position: "absolute",
            left: -5,
            top: -5,
            width: "46%",
            height: "52%",
            borderTopWidth: 5,
            borderLeftWidth: 5,
            borderColor: accent,
            borderTopLeftRadius: 22,
          }}
        />
      </View>
    </Pressable>
  );
}
