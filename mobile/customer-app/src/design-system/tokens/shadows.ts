import { Platform } from "react-native";

interface ShadowStyle {
  shadowColor: string;
  shadowOffset: { width: number; height: number };
  shadowOpacity: number;
  shadowRadius: number;
  elevation: number;
}

function makeShadow(color: string, opacity: number, radius: number, height: number, elevation: number): ShadowStyle {
  return Platform.select<ShadowStyle>({
    default: {
      shadowColor: color,
      shadowOffset: { width: 0, height },
      shadowOpacity: opacity,
      shadowRadius: radius,
      elevation,
    },
  }) as ShadowStyle;
}

export function buildShadows(shadowColor: string) {
  return {
    none: makeShadow(shadowColor, 0, 0, 0, 0),
    sm: makeShadow(shadowColor, 0.06, 6, 2, 2),
    md: makeShadow(shadowColor, 0.1, 12, 4, 5),
    lg: makeShadow(shadowColor, 0.15, 20, 8, 10),
  } as const;
}

export type ShadowScale = ReturnType<typeof buildShadows>;
