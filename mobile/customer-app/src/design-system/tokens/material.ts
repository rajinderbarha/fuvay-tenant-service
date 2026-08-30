/**
 * Layered surface recipes — the Fuvay v2 material ramp.
 *
 * v2 is a neumorphic language: a tile is a radial-gradient outer ring with an
 * inset-shadowed inner face, and cards sit on the shell separated by a
 * hairline `outline` rather than a big luminance step. Keeping the recipes in
 * one token file prevents individual screens from inventing their own card,
 * tile, input, or navigation treatment.
 *
 * Gradient stops are condensed from the canvas's longer ramps to the 2- and
 * 3-stop tuples this interface exposes, preserving the first, middle and last
 * stop so the direction and end points of each ramp are unchanged.
 *
 * The single most important distinction, and the one that caused a real
 * regression when I first got it backwards: `raised` / `interactive` are the
 * RAISED card surfaces, while `inset` is the RECESSED input surface (search
 * field, AI prompt rows). In light mode a recess goes brighter (toward
 * white); in dark mode it goes darker. See tokens/colors.ts for the same
 * panel-vs-card distinction in flat colour form.
 */
export interface MaterialTokens {
  canvas: readonly [string, string];
  raised: readonly [string, string, string];
  interactive: readonly [string, string, string];
  inset: readonly [string, string];
  tileOuter: readonly [string, string, string];
  tileInner: readonly [string, string, string];
  outline: string;
  outlineStrong: string;
  highlight: string;
  shadow: string;
  shadowSoft: string;
}

export const lightMaterial: MaterialTokens = {
  // Shell -> sunken, the page ground.
  canvas: ["#f4f3f1", "#eceae7"],
  // The v2 header/panel ramp: white falling to a warm off-white.
  raised: ["#ffffff", "#f8f6f4", "#f0eeeb"],
  interactive: ["#ffffff", "#faf9f7", "#f4f2ef"],
  // Recessed input surface -- brighter than the panel in light mode.
  inset: ["#f4f2ef", "#edebe7"],
  tileOuter: ["#ecebe8", "#f4f2f0", "#d6d2cd"],
  tileInner: ["#fbfaf9", "#f4f2ef", "#e4e0db"],
  outline: "rgba(120, 110, 100, 0.14)",
  outlineStrong: "rgba(90, 82, 74, 0.28)",
  highlight: "rgba(255, 255, 255, 0.9)",
  shadow: "rgba(60, 52, 44, 0.35)",
  shadowSoft: "rgba(60, 52, 44, 0.2)",
};

export const darkMaterial: MaterialTokens = {
  canvas: ["#232326", "#1d1d20"],
  raised: ["#313137", "#2a2a2e", "#232326"],
  interactive: ["#2b2b2f", "#26262a", "#232326"],
  // Recessed input surface -- darker than the panel in dark mode.
  inset: ["#26262a", "#232326"],
  tileOuter: ["#262629", "#35353c", "#1f1f22"],
  tileInner: ["#34343a", "#2e2e33", "#232326"],
  outline: "rgba(255, 255, 255, 0.07)",
  outlineStrong: "rgba(255, 255, 255, 0.09)",
  highlight: "rgba(255, 255, 255, 0.06)",
  shadow: "rgba(0, 0, 0, 0.8)",
  shadowSoft: "rgba(0, 0, 0, 0.55)",
};
