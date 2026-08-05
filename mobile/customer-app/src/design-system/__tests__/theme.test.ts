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
    expect(theme.typography.body.fontSize).toBe(15);
    expect(theme.touchTargets.minimum).toBeGreaterThanOrEqual(44);
  });
});
