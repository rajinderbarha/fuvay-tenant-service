import { lightColors, darkColors, ColorTokens } from "../tokens/colors";
import { spacing, layout } from "../tokens/spacing";
import { radius, radiusUsage } from "../tokens/radius";
import { typography } from "../tokens/typography";
import { buildShadows } from "../tokens/shadows";
import { motion } from "../tokens/motion";
import { opacity } from "../tokens/opacity";
import { zIndex } from "../tokens/zIndex";
import { iconSizes } from "../tokens/iconSizes";

export type ThemeMode = "light" | "dark";

export function buildTheme(mode: ThemeMode) {
  const colors: ColorTokens = mode === "dark" ? darkColors : lightColors;
  return {
    mode,
    colors,
    spacing,
    layout,
    radius,
    radiusUsage,
    typography,
    shadow: buildShadows(mode),
    motion,
    opacity,
    zIndex,
    iconSizes,
  } as const;
}

export type Theme = ReturnType<typeof buildTheme>;
