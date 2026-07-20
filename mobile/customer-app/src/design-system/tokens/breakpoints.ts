/**
 * Mobile-layout breakpoints, not web breakpoints. Widths represent typical
 * device logical-pixel widths, not arbitrary round numbers.
 */
export const breakpoints = {
  compact: 0, // small phones (e.g. iPhone SE, ~360dp wide)
  regular: 400, // standard phones
  large: 600, // large phones / small foldables unfolded
  tablet: 768, // tablets / large foldables
} as const;

export type BreakpointKey = keyof typeof breakpoints;

export function classifyWidth(width: number): BreakpointKey {
  if (width >= breakpoints.tablet) return "tablet";
  if (width >= breakpoints.large) return "large";
  if (width >= breakpoints.regular) return "regular";
  return "compact";
}
