import { lightColors, darkColors } from "../tokens/colors";

/**
 * Customer native design tokens: restrained brand blue for actions, a warm
 * neutral canvas, multicolour campaign content, and a deep charcoal dark
 * theme. These guards protect contrast without forcing campaign artwork or
 * service imagery into the brand colour.
 *
 * This also re-fixed the real, user-visible chat defect this file
 * originally guarded: `surfaceDefault` (chat bubbles) must never be
 * identical to `backgroundPrimary` (the screen behind it), in either
 * theme, or assistant bubbles become invisible. The structural invariants
 * below (contrast, distinct surface/background, near-black not
 * pure-black dark bg) are what actually matter and are asserted
 * independently of the specific hex values.
 */
/** WCAG relative luminance + contrast ratio, used by the guards below. */
function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map(c =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4),
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

describe("customer native brand and contrast tokens", () => {
  it("uses the Fuvay v2 blue (a2) as the brand fill, brighter in dark mode", () => {
    // v2's a2 accent -- the canvas uses it for every primary action.
    expect(lightColors.brandPrimary).toBe("#1a63a8");
    expect(darkColors.brandPrimary).toBe("#3f9bf0");
    // Dark mode must be the brighter of the two, so a filled button reads
    // as raised against a dark shell rather than sinking into it.
    expect(relativeLuminance(darkColors.brandPrimary)).toBeGreaterThan(
      relativeLuminance(lightColors.brandPrimary),
    );
  });

  /**
   * The invariant that actually protects users, asserted independently of
   * any specific hex: whatever sits ON the brand fill must be readable
   * against it. Blue has enough luminance contrast for white text/icons,
   * unlike the previous yellow which needed dark ink.
   */
  it("keeps text on the brand fill readable in both themes", () => {
    for (const theme of [lightColors, darkColors]) {
      expect(contrastRatio(theme.brandOnPrimary, theme.brandPrimary)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("keeps brand-coloured text readable on the page background in both themes", () => {
    for (const theme of [lightColors, darkColors]) {
      expect(contrastRatio(theme.brandPrimaryStrong, theme.backgroundPrimary)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(theme.textLink, theme.backgroundPrimary)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("keeps the foreground brand shade in the same blue family as the fill", () => {
    // Same hue family: blue >= red and blue >= green for both, so the
    // foreground shade still reads as the brand colour, not a new one.
    for (const hex of [lightColors.brandPrimaryStrong, lightColors.brandPrimary]) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      expect(b).toBeGreaterThanOrEqual(r);
      expect(b).toBeGreaterThanOrEqual(g);
    }
  });

  it("maps semantic status colors onto the v2 accent rotation", () => {
    // success = a3 (green), warning = a1 (amber). Danger has no v2 accent
    // -- none of a1-a4 may signal destruction -- so it is a hue-matched
    // addition, asserted for contrast rather than identity alone.
    expect(lightColors.statusSuccess).toBe("#207c4a");
    expect(lightColors.statusWarning).toBe("#9c6209");
    expect(darkColors.statusSuccess).toBe("#4ecb7c");
    expect(darkColors.statusWarning).toBe("#f0b429");
    for (const theme of [lightColors, darkColors]) {
      expect(contrastRatio(theme.statusDanger, theme.backgroundPrimary)).toBeGreaterThanOrEqual(3);
    }
  });

  it("uses the v2 neutral shell (not pure-black) as the dark background", () => {
    expect(darkColors.backgroundPrimary).toBe("#232326");
    expect(darkColors.backgroundPrimary).not.toBe("#000000");
  });

  it("gives dark-mode cards a visible border distinct from the background (elevation via layering, not glow)", () => {
    expect(darkColors.surfaceDefault).not.toBe(darkColors.backgroundPrimary);
    expect(darkColors.borderDefault).not.toBe(darkColors.surfaceDefault);
  });

  it("never uses pure white or a background identical to the surface it must contrast against", () => {
    expect(lightColors.backgroundPrimary).not.toBe("#FFFFFF");
    expect(lightColors.backgroundPrimary).not.toBe(lightColors.surfaceDefault);
    expect(darkColors.backgroundPrimary).not.toBe(darkColors.surfaceDefault);
  });

  it("keeps dark-mode primary text close to white, not washed-out gray", () => {
    expect(darkColors.textPrimary).toBe("#f0f0f2");
    // The real requirement: near-white, and comfortably readable on the shell.
    expect(relativeLuminance(darkColors.textPrimary)).toBeGreaterThan(0.8);
    expect(
      contrastRatio(darkColors.textPrimary, darkColors.backgroundPrimary),
    ).toBeGreaterThanOrEqual(7);
  });

  it("defines distinct campaign tokens for light and dark treatments", () => {
    // v2 campaigns are amber-washed (a1), and the hex "OFF" badge is a
    // fixed amber in BOTH themes -- so its foreground is computed, not
    // theme-flipped.
    expect(lightColors.campaignBackground).toBe("#9c620918");
    expect(darkColors.campaignGradientStart).not.toBe(lightColors.campaignBackground);
    expect(lightColors.campaignAccent).toBe(darkColors.campaignAccent);
    for (const theme of [lightColors, darkColors]) {
      expect(
        contrastRatio(theme.campaignBadgeForeground, theme.campaignAccent),
      ).toBeGreaterThanOrEqual(4.5);
    }
  });

  /**
   * The actual chat-legibility regression guard: an assistant chat bubble
   * (`surfaceDefault`) must be genuinely distinguishable from the
   * conversation background (`backgroundPrimary`) it sits on, in BOTH
   * themes. A near-identical pair is exactly what made bubbles invisible
   * (twice now -- this is the second time this exact regression happened).
   */
  it("keeps chat-bubble surfaces legibly separated from the conversation background", () => {
    function luminance(hex: string): number {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    for (const theme of [lightColors, darkColors]) {
      const delta = Math.abs(luminance(theme.surfaceDefault) - luminance(theme.backgroundPrimary));
      expect(delta).toBeGreaterThan(5);
    }
  });
});
