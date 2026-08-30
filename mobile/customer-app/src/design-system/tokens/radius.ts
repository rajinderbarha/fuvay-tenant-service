/**
 * Corner radii — Fuvay v2.
 *
 * v2 is markedly rounder than the previous scale: cards are 20-22px (was
 * 20), inputs and inner tiles 14-18px (was 14), and every button, chip and
 * badge is a full pill. The phone shell itself is 34px.
 *
 * `radiusTile` is deliberately not in px. v2 tiles use a PERCENTAGE radius
 * (30% outer / 27% inner) so the squircle keeps its proportions at any tile
 * size — a fixed px radius on a 46px avatar tile and a 82px specialist tile
 * would read as two different shapes.
 */
export const radius = {
  radiusSmall: 8,
  radiusMedium: 14,
  radiusLarge: 20,
  radiusXLarge: 22,
  /** Phone shell / full-bleed sheet. */
  radiusShell: 34,
  radiusPill: 999,
  radiusFull: 9999,
};

/** Squircle radii expressed as a percentage of the tile's own size. */
export const radiusTile = {
  outer: "30%",
  inner: "27%",
} as const;

export const radiusUsage = {
  input: radius.radiusMedium,
  button: radius.radiusPill,
  card: radius.radiusLarge,
  panel: radius.radiusXLarge,
  sheet: radius.radiusShell,
  statusPill: radius.radiusPill,
  avatar: radius.radiusFull,
};
