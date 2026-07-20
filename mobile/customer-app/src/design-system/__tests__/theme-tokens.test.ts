import { lightTheme } from "../themes/light-theme";
import { darkTheme } from "../themes/dark-theme";
import { REQUIRED_SEMANTIC_COLOR_KEYS } from "../themes/theme-types";

describe("semantic color tokens", () => {
  it("light theme defines every required semantic key", () => {
    const missing = REQUIRED_SEMANTIC_COLOR_KEYS.filter((key) => !(key in lightTheme.colors));
    expect(missing).toEqual([]);
  });

  it("dark theme defines every required semantic key", () => {
    const missing = REQUIRED_SEMANTIC_COLOR_KEYS.filter((key) => !(key in darkTheme.colors));
    expect(missing).toEqual([]);
  });

  it("light and dark themes expose an identical key structure", () => {
    expect(Object.keys(lightTheme.colors).sort()).toEqual(Object.keys(darkTheme.colors).sort());
  });

  it("every semantic color value is a non-empty, valid CSS color string", () => {
    const colorPattern = /^#([0-9a-fA-F]{3,8})$|^rgba?\(/;
    for (const theme of [lightTheme, darkTheme]) {
      for (const [key, value] of Object.entries(theme.colors)) {
        expect(typeof value).toBe("string");
        expect(value.length).toBeGreaterThan(0);
        expect(colorPattern.test(value)).toBe(true);
      }
    }
  });

  it("light and dark themes do not share identical background colors (real dark mode, not a hue tweak)", () => {
    expect(lightTheme.colors.backgroundPrimary).not.toBe(darkTheme.colors.backgroundPrimary);
    expect(lightTheme.colors.surfacePrimary).not.toBe(darkTheme.colors.surfacePrimary);
  });

  it("dark theme shadow color is not the brand-tinted light shadow color", () => {
    expect(darkTheme.shadows.md.shadowColor).not.toBe(lightTheme.shadows.md.shadowColor);
  });
});
