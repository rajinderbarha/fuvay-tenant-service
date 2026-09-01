import { lightColors, darkColors, ColorTokens } from "../tokens/colors";
import { spacing, layout } from "../tokens/spacing";
import { radius, radiusUsage } from "../tokens/radius";
import { typography } from "../tokens/typography";
import { buildShadows } from "../tokens/shadows";
import { motion } from "../tokens/motion";
import { opacity } from "../tokens/opacity";
import { iconSizes } from "../tokens/iconSizes";
import { touchTargets } from "../tokens/touchTargets";
import { darkMaterial, lightMaterial } from "../tokens/material";
import { componentMetrics } from "../tokens/components";
import { darkEditorialPalettes, lightEditorialPalettes } from "../tokens/editorial";
import { buildFuvayTheme } from "../tokens/fuvay";

export type ThemeMode = "light" | "dark";

export function buildTheme(mode: ThemeMode) {
  const colors: ColorTokens = mode === "dark" ? darkColors : lightColors;
  const material = mode === "dark" ? darkMaterial : lightMaterial;
  const editorial = mode === "dark" ? darkEditorialPalettes : lightEditorialPalettes;
  const fuvay = buildFuvayTheme(mode === "dark");
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
    iconSizes,
    touchTargets,
    material,
    metrics: componentMetrics,
    editorial,
    fuvay,
  } as const;
}

export type Theme = ReturnType<typeof buildTheme>;
