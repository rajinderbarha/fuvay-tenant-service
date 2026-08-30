/** Base spacing scale -- all layout spacing must come from here or the
 * semantic layout helpers below, never a raw literal in a screen. */
export const spacing = {
  none: 0,
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
  xxxl: 40,
  huge: 48,
} as const;

/** Semantic layout helpers -- name the intent, not the pixel value. */
export const layout = {
  screenHorizontalPadding: spacing.base,
  sectionSpacing: spacing.xl,
  cardPadding: spacing.base,
  rowGap: spacing.sm,
  inlineGap: spacing.xs,
  compactGap: spacing.xxs,
  minTouchTarget: 48,
  /** Authentication uses one responsive shell across OTP and password.
   * Keeping these dimensions here prevents either route from inventing its
   * own logo, form, artwork or footer size. */
  authContentMaxWidth: 440,
  authCompactWidthBreakpoint: 360,
  authCompactHeightBreakpoint: 720,
  authLogoMaxWidth: 260,
  authLogoCompactWidth: 216,
  authCityArtworkHeight: 112,
  authFooterMinHeight: 188,
} as const;

export type SpacingToken = keyof typeof spacing;
