import { useTheme } from "../../design-system/theme";

/**
 * Maps the app's own light/dark design-system tokens onto the names this
 * chat's components already use, so the merged booking bot follows the
 * user's system/light/dark theme preference like every other screen
 * instead of forcing a bespoke always-dark palette.
 */
export function useBotColors() {
  const { theme } = useTheme();
  const c = theme.colors;
  const f = theme.fuvay;
  return {
    bg: f.surfaces.shell,
    bgComposer: f.surfaces.panel,
    surface: f.surfaces.card,
    surfaceRaised: f.surfaces.panel,
    surfaceSunken: f.surfaces.card,
    surfaceActive: f.soft(f.accents.a2),
    border: f.surfaces.edge,
    borderSubtle: f.surfaces.edge,
    borderActive: f.accents.a2,
    textPrimary: f.surfaces.text,
    textSecondary: f.surfaces.sub,
    textTertiary: f.surfaces.faint,
    textMuted: f.surfaces.sub,
    textDim: f.surfaces.faint,
    textFaint: f.surfaces.faint,
    stepDone: f.surfaces.sub,
    brand: f.accents.a2,
    brandLight: f.accents.a2,
    brandTint: f.soft(f.accents.a2),
    bubbleOnBrand: f.ink(f.accents.a2),
    success: f.accents.a3,
    successBg: f.soft(f.accents.a3),
    // These three must NOT all resolve to the same value: the confirmation
    // card is a success-surface panel, so a success-surface border and a
    // success-surface icon circle would both be invisible against it.
    successBorder: f.accents.a3,
    successTint: f.surfaces.card,
    warning: f.accents.a1,
    danger: c.statusDanger,
  };
}

export type BotColors = ReturnType<typeof useBotColors>;
