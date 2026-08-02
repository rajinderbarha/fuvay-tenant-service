export const radius = {
  radiusSmall: 6,
  radiusMedium: 10,
  radiusLarge: 16,
  radiusPill: 999,
  radiusFull: 9999,
} as const;

/** Recommended usage -- see section 12 of the foundation spec. */
export const radiusUsage = {
  input: radius.radiusMedium,
  button: radius.radiusMedium,
  card: radius.radiusLarge,
  statusPill: radius.radiusPill,
  avatar: radius.radiusFull,
} as const;
