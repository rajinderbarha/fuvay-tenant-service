import { buildTheme } from "../theme/buildTheme";
import { lightColors, darkColors } from "../tokens/colors";

describe("buildTheme", () => {
  it("resolves the light palette for mode='light'", () => {
    const theme = buildTheme("light");
    expect(theme.mode).toBe("light");
    expect(theme.colors).toEqual(lightColors);
  });

  it("resolves the dark palette for mode='dark'", () => {
    const theme = buildTheme("dark");
    expect(theme.mode).toBe("dark");
    expect(theme.colors).toEqual(darkColors);
  });

  it("exposes tokens consumers rely on instead of inline literals", () => {
    const theme = buildTheme("light");
    expect(theme.spacing.base).toBe(16);
    expect(theme.radiusUsage.card).toBe(theme.radius.radiusLarge);
    // v2 runs tighter than the previous scale (body 15 -> 13).
    expect(theme.typography.body.fontSize).toBe(13);
    // What actually matters: the scale stays ordered and legible.
    expect(theme.typography.body.fontSize!).toBeGreaterThanOrEqual(12);
    expect(theme.typography.headingLarge.fontSize!).toBeGreaterThan(
      theme.typography.body.fontSize!,
    );
    // v2 sets Barlow explicitly per style -- weight comes from the family
    // name, so a missing fontFamily would silently fall back to system font.
    expect(theme.typography.body.fontFamily).toContain("Barlow");
    expect(theme.touchTargets.minimum).toBeGreaterThanOrEqual(44);
    expect(theme.layout.authLogoMaxWidth).toBeGreaterThan(theme.layout.authLogoCompactWidth);
    expect(theme.layout.authContentMaxWidth).toBeGreaterThan(theme.layout.authCompactWidthBreakpoint);
    expect(theme.layout.authFooterMinHeight).toBeGreaterThan(theme.touchTargets.comfortable);
    expect(theme.material.raised).toHaveLength(3);
    expect(theme.material.tileOuter).toHaveLength(3);
  });

  it("uses distinct layered material recipes in light and dark mode", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    expect(light.material.canvas).not.toEqual(dark.material.canvas);
    expect(light.material.raised[0]).not.toBe(light.material.raised[2]);
    expect(dark.material.raised[0]).not.toBe(dark.material.raised[2]);
    expect(light.colors.brandPrimary).toBe("#0f6b60");
    expect(dark.colors.brandPrimary).toBe("#2f9e8f");
  });
});
