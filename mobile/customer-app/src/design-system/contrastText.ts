/**
 * Readable text colour for an arbitrary background.
 *
 * Needed because campaign accents are chosen by an admin, not by the design
 * system: `#f59e0b` wants near-black on it, `#7c3aed` wants white, and the theme
 * cannot know which was picked. Hardcoding white produced unreadable labels on
 * light accents -- an accessibility bug that only shows up for whichever colour
 * the admin happens to choose, which is the worst kind to ship.
 *
 * Uses WCAG relative luminance rather than a naive average: the eye is far more
 * sensitive to green than to blue, so averaging the channels misjudges exactly
 * the mid-tone accents where the decision is closest.
 */

const NEAR_BLACK = "#1A1A1A";
const WHITE = "#FFFFFF";

/** Luminance at which white text and near-black text give equal WCAG contrast
 * against the background. Above it, dark text wins.
 *
 * 0.179, not a midpoint guess: contrast is a ratio of (L + 0.05), so the
 * crossover sits far below 0.5. An earlier 0.45 here chose WHITE on amber
 * (#f59e0b), which is 2.1:1 -- failing even large-text AA -- where near-black is
 * 9.7:1. Mid-tone accents are exactly where the decision matters, so the
 * threshold has to come from the contrast formula rather than intuition. */
const LIGHT_THRESHOLD = 0.179;

export function onColor(background: string | null | undefined, fallback = WHITE): string {
  const rgb = parseHex(background);
  if (!rgb) return fallback;
  return relativeLuminance(rgb) > LIGHT_THRESHOLD ? NEAR_BLACK : WHITE;
}

function parseHex(value: string | null | undefined): [number, number, number] | null {
  if (!value) return null;
  let hex = value.trim().replace("#", "");
  // #abc shorthand, and #aabbccdd with an alpha suffix the caller may have
  // appended for a wash -- alpha does not affect which text is readable on the
  // opaque fill, so it is dropped.
  if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
  if (hex.length === 8) hex = hex.slice(0, 6);
  if (hex.length !== 6 || /[^0-9a-f]/i.test(hex)) return null;
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const [rl, gl, bl] = [r, g, b].map(channel => {
    const c = channel / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl;
}
