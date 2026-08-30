import {
  buildFuvayTheme,
  darkAccents,
  ink,
  lightAccents,
  softAccent,
} from "../tokens/fuvay";

/**
 * `ink()` is ported from the design canvas and every filled pill in the v2
 * screens depends on it. A silent drift here means unreadable text on a
 * coloured button, so the contrast maths is asserted directly rather than
 * trusted.
 */
describe("ink() — WCAG on-colour selection", () => {
  /** Independent re-implementation of WCAG 2.1 contrast, used to check
   *  ink() actually returns the better of the two options rather than
   *  merely returning what it returned yesterday. */
  function luminance(hex: string): number {
    const c = [1, 3, 5]
      .map((k) => parseInt(hex.substr(k, 2), 16) / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function ratio(a: string, b: string): number {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  }

  const everyAccent = [
    ...Object.values(darkAccents),
    ...Object.values(lightAccents),
  ];

  it.each(everyAccent)("picks the higher-contrast foreground for %s", (accent) => {
    const chosen = ink(accent);
    const other = chosen === "#ffffff" ? "#14141a" : "#ffffff";
    expect(ratio(chosen, accent)).toBeGreaterThanOrEqual(ratio(other, accent));
  });

  it.each(everyAccent)("reaches WCAG AA (4.5:1) on %s", (accent) => {
    expect(ratio(ink(accent), accent)).toBeGreaterThanOrEqual(4.5);
  });

  it("matches the canvas on the specific accents it shipped", () => {
    // Dark amber/green are light colours -> dark ink; dark blue/violet and
    // every light-theme accent are dark enough for white.
    expect(ink("#f0b429")).toBe("#14141a");
    expect(ink("#4ecb7c")).toBe("#14141a");
    expect(ink("#3f9bf0")).toBe("#14141a");
    expect(ink("#a875f5")).toBe("#14141a");
    expect(ink("#9c6209")).toBe("#ffffff");
    expect(ink("#1a63a8")).toBe("#ffffff");
    expect(ink("#207c4a")).toBe("#ffffff");
    expect(ink("#6c37b3")).toBe("#ffffff");
  });

  it("returns near-black, never pure black, matching the canvas", () => {
    const darkResults = everyAccent.map(ink).filter((v) => v !== "#ffffff");
    expect(darkResults.length).toBeGreaterThan(0);
    darkResults.forEach((v) => expect(v).toBe("#14141a"));
  });
});

describe("softAccent()", () => {
  it("produces 8-digit hex RN can parse", () => {
    expect(softAccent("#3f9bf0", true)).toBe("#3f9bf01f");
    expect(softAccent("#1a63a8", false)).toBe("#1a63a818");
  });

  it("is more transparent in light mode than dark", () => {
    const darkAlpha = parseInt(softAccent("#3f9bf0", true).slice(-2), 16);
    const lightAlpha = parseInt(softAccent("#3f9bf0", false).slice(-2), 16);
    expect(lightAlpha).toBeLessThan(darkAlpha);
  });
});

describe("buildFuvayTheme()", () => {
  it("binds soft() to the theme so callers cannot mix alphas", () => {
    expect(buildFuvayTheme(true).soft("#3f9bf0")).toBe("#3f9bf01f");
    expect(buildFuvayTheme(false).soft("#3f9bf0")).toBe("#3f9bf018");
  });

  it("light accents are darker than dark accents (not merely dimmed)", () => {
    // The light theme needs accents legible AS TEXT on a pale surface, so
    // each must be genuinely darker than its dark-theme counterpart.
    (Object.keys(darkAccents) as (keyof typeof darkAccents)[]).forEach((k) => {
      expect(luminanceOf(lightAccents[k])).toBeLessThan(luminanceOf(darkAccents[k]));
    });
    function luminanceOf(hex: string): number {
      const c = [1, 3, 5]
        .map((n) => parseInt(hex.substr(n, 2), 16) / 255)
        .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    }
  });

  /**
   * Light accents exist to be readable AS TEXT on pale surfaces -- the
   * canvas puts them on eyebrow labels ("LIMITED OFFER") sitting directly
   * on a panel. Every light surface is checked, not just white: the
   * canvas's own #a3670a passed on white but failed on panel and shell,
   * which is why lightAccents.a1 is #9c6209 here.
   */
  describe.each([
    ["shell", "#f4f3f1"],
    ["panel", "#faf9f7"],
    ["card", "#ffffff"],
  ])("light accents as text on %s", (_name, surface) => {
    function lum(hex: string): number {
      const c = [1, 3, 5]
        .map((n) => parseInt(hex.substr(n, 2), 16) / 255)
        .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    }
    it.each(Object.entries(lightAccents))("%s passes AA", (_key, accent) => {
      const [hi, lo] = [lum(accent), lum(surface)].sort((a, b) => b - a);
      expect((hi + 0.05) / (lo + 0.05)).toBeGreaterThanOrEqual(4.5);
    });
  });
});
