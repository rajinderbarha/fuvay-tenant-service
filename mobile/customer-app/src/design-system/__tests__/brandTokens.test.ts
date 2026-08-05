import { lightColors, darkColors } from "../tokens/colors";

/**
 * 2026-08-04 rebrand: the customer app's palette moved from warm orange
 * (#F2994A, aligned to the Staff app) to blue, matching
 * frontend/customer-app, frontend/super-admin and frontend/tenant-portal's
 * globals.css. Dark mode follows the Tesla-app reference (neutral
 * charcoal-black, electric-blue accent).
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

describe("brand tokens (blue rebrand, Tesla-app-aligned dark mode)", () => {
  it("uses the approved blue brand fill in both themes (brighter blue in dark mode)", () => {
    expect(lightColors.brandPrimary).toBe("#3868E0");
    expect(darkColors.brandPrimary).toBe("#1A6FE0");
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

  it("uses the approved semantic status colors", () => {
    expect(lightColors.statusSuccess).toBe("#1E8E5A");
    expect(lightColors.statusWarning).toBe("#B5750B");
    expect(lightColors.statusDanger).toBe("#C4342A");
  });

  it("uses a near-black (not pure-black) dark background, per the Tesla-app reference", () => {
    expect(darkColors.backgroundPrimary).toBe("#1C1C1E");
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

  it("keeps dark-mode primary text close to warm white, not washed-out gray", () => {
    expect(darkColors.textPrimary).toBe("#F5F5F7");
  });

  it("defines distinct campaign tokens for light and dark treatments", () => {
    expect(lightColors.campaignBackground).toBe("#EEF3FF");
    expect(darkColors.campaignGradientStart).not.toBe(lightColors.campaignBackground);
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
