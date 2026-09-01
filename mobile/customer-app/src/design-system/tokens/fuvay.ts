/**
 * Fuvay v2 design language — the token layer behind the "Fuvay App Screens"
 * canvas (Home, Splash, Login, AI booking assistant).
 *
 * Three things here are genuinely different from the previous token set and
 * are the reason this file exists rather than more entries in colors.ts:
 *
 * 1. FOUR ROTATING ACCENTS, not one brand colour. The design assigns a1-a4
 *    per card/category/stage so a list reads as varied without the shell
 *    changing colour. Light mode is NOT the dark palette dimmed -- each
 *    accent has a separately chosen darker value that stays legible as text
 *    on a light surface (the same problem the old `brandPrimaryStrong`
 *    solved for a single hue, now solved four times).
 *
 * 2. `ink()` COMPUTES the on-colour instead of hardcoding it. Every accent
 *    can back a filled pill, and with four accents x two themes a static
 *    pairing table would be eight values that drift. Relative luminance per
 *    WCAG 2.1 picks black or white, so a new accent is automatically safe.
 *
 * 3. NEUMORPHIC SURFACES. Tiles are a radial-gradient "outer" ring plus an
 *    inset-shadowed "inner" face. React Native cannot express either as a
 *    plain colour, so these are exported as structured descriptors that
 *    components turn into <LinearGradient> + shadow props -- they are
 *    deliberately not `string` colours.
 */

/** Accent set. Dark values are the canvas source; light values are the
 *  darkened equivalents the canvas uses for its light theme. */
export interface AccentSet {
  /** Amber — offers, ratings, warmth. */
  a1: string;
  /** Blue — primary actions, navigation, the closest thing to "brand". */
  a2: string;
  /** Green — success, verification, safety. */
  a3: string;
  /** Violet — premium, seasonal, editorial. */
  a4: string;
}

export const darkAccents: AccentSet = {
  a1: "#f0b429",
  a2: "#3f9bf0",
  a3: "#4ecb7c",
  a4: "#a875f5",
};

/** Fixed official mark colours. These do not theme-switch; they are part of
 * the Fuvay asset specification. */
export const fuvayBrand = {
  electricBlue: "#0563fe",
  deepNavy: "#02154a",
  darkMarkInk: "#ffffff",
  lightMarkInk: "#22262e",
} as const;

export const lightAccents: AccentSet = {
  /**
   * DELIBERATE DIVERGENCE from the canvas, which specifies #a3670a.
   *
   * That value fails WCAG AA as text on the light theme's own tinted
   * surfaces -- 4.43:1 on `panel` (#faf9f7) and 4.21:1 on `shell`
   * (#f4f3f1), against the 4.5:1 minimum. It only passes on pure white
   * (4.66:1), and the canvas uses a1 for label text directly on a panel
   * (the "LIMITED OFFER" eyebrow), so the failing combination is one the
   * design actually ships.
   *
   * #9c6209 is the smallest darkening that clears AA on every light
   * surface (4.55 shell / 4.79 panel / 5.04 card) and is visually the same
   * amber. Locked by a test in __tests__/fuvay.test.ts.
   */
  a1: "#9c6209",
  a2: "#1a63a8",
  a3: "#207c4a",
  a4: "#6c37b3",
};

/**
 * Foreground colour for content sitting ON a filled accent, chosen by WCAG
 * 2.1 relative luminance rather than a lookup table.
 *
 * Returns whichever of white/near-black has the better contrast ratio
 * against `hex`. Mirrors the canvas `ink()` exactly, including its
 * near-black (#14141a) rather than pure black.
 */
export function ink(hex: string): string {
  const channels = [1, 3, 5]
    .map((k) => parseInt(hex.substr(k, 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  const L = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  // Contrast of white-on-colour vs near-black-on-colour; higher wins.
  return 1.05 / (L + 0.05) > (L + 0.05) / 0.05 ? "#ffffff" : "#14141a";
}

/**
 * Translucent wash of an accent, for chip and badge backgrounds.
 *
 * The canvas appends an alpha suffix to the hex (`1f` dark / `18` light) —
 * 8-digit hex is valid in React Native, so this keeps that behaviour rather
 * than converting to rgba() and losing the 1:1 correspondence with the
 * design source.
 */
export function softAccent(hex: string, isDark: boolean): string {
  return hex + (isDark ? "1f" : "18");
}

/** A neumorphic tile: a gradient ring with an inset-shadowed inner face.
 *  Structured, not a colour string — see the file header. */
export interface TileSurface {
  /** Radial ring stops, outermost last. Feed to a gradient component. */
  outerStops: string[];
  /** Vertical gradient stops for the recessed inner face. */
  innerStops: string[];
  /** Elevation for the outer ring. */
  outerShadow: { color: string; offsetY: number; radius: number; opacity: number };
  /** Hairline + highlight drawn inside the inner face. */
  innerHairline: string;
  innerHighlight: string;
  /** Default glyph colour on an unaccented tile. */
  icon: string;
}

export const darkTile: TileSurface = {
  outerStops: ["#262629", "#29292d", "#35353c", "#40404a", "#33333a", "#1f1f22"],
  innerStops: ["#34343a", "#2e2e33", "#29292d", "#232326"],
  outerShadow: { color: "#000000", offsetY: 10, radius: 16, opacity: 0.7 },
  innerHairline: "rgba(0,0,0,0.35)",
  innerHighlight: "rgba(255,255,255,0.06)",
  icon: "#c8c8d0",
};

export const lightTile: TileSurface = {
  outerStops: ["#ecebe8", "#e9e7e4", "#f4f2f0", "#fbfaf9", "#f2f0ed", "#d6d2cd"],
  innerStops: ["#fbfaf9", "#f4f2ef", "#edebe7", "#e4e0db"],
  outerShadow: { color: "#3c342c", offsetY: 10, radius: 16, opacity: 0.28 },
  innerHairline: "rgba(120,110,100,0.14)",
  innerHighlight: "rgba(255,255,255,0.9)",
  icon: "#3c3c44",
};

/** Standalone 30%-radius plate from Circle Tile Light + Dark. Unlike the
 * ringed quick-action tile, this is one continuous gradient face. */
export interface SquircleTileSurface {
  stops: readonly [string, string, string, string];
  hairline: string;
  highlight: string;
  shade: string;
  shadow: { color: string; offsetY: number; radius: number; opacity: number };
}

export const darkSquircleTile: SquircleTileSurface = {
  stops: ["#34343a", "#2e2e33", "#29292d", "#232326"],
  hairline: "rgba(0,0,0,0.4)",
  highlight: "rgba(255,255,255,0.07)",
  shade: "rgba(0,0,0,0.4)",
  shadow: { color: "#000000", offsetY: 10, radius: 16, opacity: 0.5 },
};

export const lightSquircleTile: SquircleTileSurface = {
  stops: ["#ffffff", "#fbfaf8", "#f7f5f2", "#f1efeb"],
  hairline: "rgba(120,110,100,0.12)",
  highlight: "rgba(255,255,255,0.9)",
  shade: "rgba(120,110,100,0.035)",
  shadow: { color: "transparent", offsetY: 0, radius: 0, opacity: 0 },
};

/** Coloured-corner card treatment from the supplied service-card set. */
export interface ServiceCardSurface {
  stops: readonly [string, string, string];
  hairline: string;
  highlight: string;
  shadow: { color: string; offsetY: number; radius: number; opacity: number };
}

export const darkServiceCard: ServiceCardSurface = {
  stops: ["#34343a", "#2c2c31", "#242427"],
  hairline: "rgba(0,0,0,0.35)",
  highlight: "rgba(255,255,255,0.06)",
  shadow: { color: "#000000", offsetY: 16, radius: 26, opacity: 0.65 },
};

export const lightServiceCard: ServiceCardSurface = {
  stops: ["#ffffff", "#f7f5f3", "#eeebe7"],
  hairline: "rgba(120,110,100,0.1)",
  highlight: "rgba(255,255,255,0.9)",
  shadow: { color: "#8f867d", offsetY: 8, radius: 14, opacity: 0.1 },
};

/** React Native coordinates equivalent to the CSS gradients in the canvas. */
export const fuvayGradientGeometry = {
  css170Start: { x: 0.59, y: 0 },
  css170End: { x: 0.41, y: 1 },
  verticalStart: { x: 0.5, y: 0 },
  verticalEnd: { x: 0.5, y: 1 },
  bottomLeftStart: { x: 0, y: 1 },
  topRightEnd: { x: 1, y: 0 },
} as const;

/** Rotated rounded plate used only by the Home "Browse by category" grid.
 * Values are transcribed from Circle Tile Light + Dark.dc.html. */
export interface DiamondTileSurface {
  ghostBorder: string;
  ghostFill: string;
  plateBorder: string;
  plateStops: readonly [string, string, string];
  innerHighlight: string;
  innerShade: string;
  innerHairline: string;
  label: string;
  shadow: { color: string; offsetY: number; radius: number; opacity: number };
}

export const darkDiamondTile: DiamondTileSurface = {
  ghostBorder: "#33333a",
  ghostFill: "#26262a",
  plateBorder: "#1f1f22",
  plateStops: ["#35353b", "#2d2d32", "#232326"],
  innerHighlight: "rgba(255,255,255,0.07)",
  innerShade: "rgba(0,0,0,0.4)",
  innerHairline: "rgba(0,0,0,0.35)",
  label: "#e8e8ea",
  shadow: { color: "#000000", offsetY: 8, radius: 11, opacity: 0.55 },
};

export const lightDiamondTile: DiamondTileSurface = {
  ghostBorder: "#dcd8d3",
  ghostFill: "#efedea",
  plateBorder: "rgba(120,110,100,0.22)",
  plateStops: ["#ffffff", "#f6f4f2", "#eae7e3"],
  innerHighlight: "rgba(255,255,255,0.9)",
  innerShade: "rgba(60,52,44,0.1)",
  innerHairline: "rgba(120,110,100,0.1)",
  label: "#33333a",
  shadow: { color: "#3c342c", offsetY: 8, radius: 11, opacity: 0.24 },
};

export const fuvayDiamondGeometry = {
  containerWidth: 104,
  containerHeight: 108,
  plateSize: 68,
  plateRadius: 16,
  plateLeft: 18,
  plateTop: 14,
  ghostLeft: 15,
  ghostTop: 18,
  contentTop: 14,
  contentHeight: 68,
  iconSize: 18,
  contentGap: 5,
  labelSize: 8.5,
  labelLineHeight: 10.5,
  labelTracking: 0.35,
} as const;

/** Shell/surface colours specific to the v2 language. These sit alongside
 *  the existing semantic tokens rather than replacing them. */
export interface FuvaySurfaces {
  shell: string;
  panel: string;
  card: string;
  hexPanel: string;
  navBg: readonly [string, string];
  headerGradient: readonly [string, string, string];
  splashGradient: readonly [string, string, string, string];
  /** Low-to-high blue wash used by full-card ambient gradients. */
  ambientGlow: readonly [string, string, string];
  glowTint: string;
  sheen: string;
  edge: string;
  rule: string;
  text: string;
  sub: string;
  faint: string;
  /** Fixed amber highlight strip — intentionally identical in both themes,
   *  as in the canvas (`hexFill`). */
  hexFill: string;
}

export const darkSurfaces: FuvaySurfaces = {
  shell: "#232326",
  panel: "#2b2b2f",
  card: "#26262a",
  hexPanel: "#33333a",
  navBg: ["#26262a", "#202023"] as const,
  headerGradient: ["#313137", "#2a2a2e", "#232326"] as const,
  splashGradient: ["#34343c", "#2b2b31", "#232326", "#1d1d20"] as const,
  ambientGlow: ["rgba(63,155,240,0)", "rgba(63,155,240,0.04)", "rgba(63,155,240,0.18)"] as const,
  glowTint: "rgba(63,155,240,0.18)",
  sheen: "rgba(255,255,255,0.28)",
  edge: "rgba(255,255,255,0.07)",
  rule: "rgba(255,255,255,0.09)",
  text: "#f0f0f2",
  sub: "rgba(255,255,255,0.5)",
  faint: "rgba(255,255,255,0.62)",
  hexFill: "#f0b429",
};

export const lightSurfaces: FuvaySurfaces = {
  shell: "#f4f3f1",
  panel: "#faf9f7",
  card: "#ffffff",
  hexPanel: "#ffffff",
  navBg: ["#ffffff", "#f2f0ed"] as const,
  headerGradient: ["#ffffff", "#f8f6f4", "#f0eeeb"] as const,
  splashGradient: ["#ffffff", "#f7f5f3", "#efedea", "#e8e5e1"] as const,
  ambientGlow: ["rgba(27,111,186,0)", "rgba(27,111,186,0.025)", "rgba(27,111,186,0.14)"] as const,
  glowTint: "rgba(27,111,186,0.14)",
  sheen: "rgba(255,255,255,0.75)",
  edge: "rgba(120,110,100,0.14)",
  rule: "rgba(90,82,74,0.14)",
  text: "#2a2a2f",
  sub: "rgba(60,52,44,0.78)",
  faint: "rgba(60,52,44,0.72)",
  hexFill: "#f0b429",
};

/**
 * Regular hexagon as a percentage polygon, for category tiles.
 * RN has no clip-path, so consumers render this via react-native-svg
 * (Polygon points) or an SVG mask. Kept as data so both do the same shape.
 */
export const HEX_POINTS = [
  [50, 0],
  [100, 25],
  [100, 75],
  [50, 100],
  [0, 75],
  [0, 25],
] as const;

/** Typography families the v2 canvas uses. Barlow for everything, JetBrains
 *  Mono exclusively for the uppercase tracked metadata labels
 *  ("NEXT VISIT", "STEP 1 OF 5") — never for body copy. */
export const fuvayFonts = {
  sans: "Barlow",
  mono: "JetBrains Mono",
} as const;

/** Letter-spacing for the mono metadata labels, which varies per usage in
 *  the canvas (0.1em - 0.24em). Expressed in px at the sizes actually used. */
export const monoTracking = {
  tight: 0.9,
  base: 1.4,
  wide: 1.9,
  widest: 2.3,
} as const;

/** Motion used by the few stateful moments in the reference design. Routine
 * cards and booking rails stay still; only a live state, chat turn, or
 * confirmation may opt in to these values. */
export const fuvayMotion = {
  livePulseMs: 1800,
  confirmationMs: 4600,
  confirmationFadeInEnd: 0.1,
  confirmationFadeOutStart: 0.84,
} as const;

export interface FuvayTheme {
  accents: AccentSet;
  surfaces: FuvaySurfaces;
  tile: TileSurface;
  squircleTile: SquircleTileSurface;
  serviceCard: ServiceCardSurface;
  diamondTile: DiamondTileSurface;
  softShadow: { color: string; offsetY: number; radius: number; opacity: number };
  motion: typeof fuvayMotion;
  isDark: boolean;
  /** Convenience: accent wash bound to this theme's alpha. */
  soft: (hex: string) => string;
  /** Convenience: re-exported so screens never import ink() separately and
   *  risk pairing it with the wrong theme. */
  ink: (hex: string) => string;
}

export function buildFuvayTheme(isDark: boolean): FuvayTheme {
  return {
    accents: isDark ? darkAccents : lightAccents,
    surfaces: isDark ? darkSurfaces : lightSurfaces,
    tile: isDark ? darkTile : lightTile,
    squircleTile: isDark ? darkSquircleTile : lightSquircleTile,
    serviceCard: isDark ? darkServiceCard : lightServiceCard,
    diamondTile: isDark ? darkDiamondTile : lightDiamondTile,
    softShadow: isDark
      ? { color: "#000000", offsetY: 8, radius: 16, opacity: 0.55 }
      : { color: "#8f867d", offsetY: 5, radius: 10, opacity: 0.1 },
    motion: fuvayMotion,
    isDark,
    soft: (hex: string) => softAccent(hex, isDark),
    ink,
  };
}
