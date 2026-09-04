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
  canvas: ["#f7f5f1", "#f0eee9"],
  // The v2 header/panel ramp: white falling to a warm off-white.
  raised: ["#ffffff", "#fbfaf8", "#f7f5f1"],
  interactive: ["#ffffff", "#fbfaf8", "#f6f4f0"],
  // Recessed input surface -- brighter than the panel in light mode.
  inset: ["#fbfaf8", "#f0eee9"],
  tileOuter: ["#f0eee9", "#f6f4f0", "#ddd8d0"],
  tileInner: ["#ffffff", "#fbfaf8", "#f0eee9"],
  outline: "#e9e5df",
  outlineStrong: "#ddd8d0",
  highlight: "rgba(255, 255, 255, 0.9)",
  shadow: "rgba(60, 52, 44, 0.35)",
  shadowSoft: "rgba(60, 52, 44, 0.2)",
};

export const darkMaterial: MaterialTokens = {
  canvas: ["#111110", "#141413"],
  raised: ["#1f1f1c", "#1a1a17", "#111110"],
  interactive: ["#1f1f1c", "#1a1a17", "#141413"],
  // Recessed input surface -- darker than the panel in dark mode.
  inset: ["#1a1a17", "#141413"],
  tileOuter: ["#1a1a17", "#262622", "#111110"],
  tileInner: ["#1f1f1c", "#1a1a17", "#141413"],
  outline: "#2c2c26",
  outlineStrong: "#33322c",
  highlight: "rgba(255, 255, 255, 0.06)",
  shadow: "rgba(0, 0, 0, 0.8)",
  shadowSoft: "rgba(0, 0, 0, 0.55)",
};
