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
  return {
    bg: c.backgroundPrimary,
    bgComposer: c.backgroundSecondary,
    surface: c.surfaceDefault,
    surfaceRaised: c.surfaceRaised,
    surfaceSunken: c.backgroundSunken,
    surfaceActive: c.surfaceSelected,
    border: c.borderDefault,
    borderSubtle: c.borderSubtle,
    borderActive: c.borderFocus,
    textPrimary: c.textPrimary,
    textSecondary: c.textSecondary,
    textTertiary: c.textTertiary,
    textMuted: c.textTertiary,
    textDim: c.textDisabled,
    textFaint: c.textDisabled,
    stepDone: c.textTertiary,
    brand: c.brandPrimary,
    brandLight: c.brandPrimaryStrong,
    brandTint: c.brandPrimaryMuted,
    bubbleOnBrand: c.brandOnPrimary,
    success: c.statusSuccess,
    successBg: c.statusSuccessSurface,
    // These three must NOT all resolve to the same value: the confirmation
    // card is a success-surface panel, so a success-surface border and a
    // success-surface icon circle would both be invisible against it.
    successBorder: c.statusSuccess,
    successTint: c.surfaceDefault,
    warning: c.statusWarning,
    danger: c.statusDanger,
  };
}

export type BotColors = ReturnType<typeof useBotColors>;
