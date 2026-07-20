export const radii = {
  none: 0,
  xs: 4,
  sm: 6,
  md: 10,
  lg: 16,
  xl: 22,
  pill: 999,
  full: 9999,
} as const;

export type RadiusKey = keyof typeof radii;
