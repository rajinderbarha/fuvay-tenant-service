import { lightColors, darkColors, ColorTokens } from "../colors";

describe("color tokens", () => {
  it("light and dark palettes define the exact same key set", () => {
    const lightKeys = Object.keys(lightColors).sort();
    const darkKeys = Object.keys(darkColors).sort();
    expect(darkKeys).toEqual(lightKeys);
  });

  it("has no key with an empty/undefined value in either palette", () => {
    for (const palette of [lightColors, darkColors]) {
      for (const [key, value] of Object.entries(palette)) {
        expect(Boolean(value)).toBe(true);
      }
    }
  });

  it("light mode is not pure white everywhere (backgroundPrimary != #FFFFFF)", () => {
    expect(lightColors.backgroundPrimary.toUpperCase()).not.toBe("#FFFFFF");
  });

  it("dark mode is not pure black everywhere (surfaceDefault != #000000)", () => {
    expect(darkColors.surfaceDefault.toUpperCase()).not.toBe("#000000");
    expect(darkColors.backgroundPrimary.toUpperCase()).not.toBe("#000000");
  });

  it("status bar style flips between palettes", () => {
    expect(lightColors.statusBarStyle).toBe("dark");
    expect(darkColors.statusBarStyle).toBe("light");
  });

  it("satisfies the ColorTokens interface (compile-time check via assignment)", () => {
    const check: ColorTokens = lightColors;
    expect(check).toBeDefined();
  });
});
