import { buildTheme } from "../buildTheme";

describe("buildTheme", () => {
  it("returns a light theme with light colors and status bar style dark", () => {
    const theme = buildTheme("light");
    expect(theme.mode).toBe("light");
    expect(theme.colors.statusBarStyle).toBe("dark");
  });

  it("returns a dark theme with dark colors and status bar style light", () => {
    const theme = buildTheme("dark");
    expect(theme.mode).toBe("dark");
    expect(theme.colors.statusBarStyle).toBe("light");
  });

  it("includes the full token set (spacing, radius, typography, shadow, motion)", () => {
    const theme = buildTheme("light");
    expect(theme.spacing.base).toBe(16);
    expect(theme.radius.radiusMedium).toBe(10);
    expect(theme.typography.body).toBeDefined();
    expect(theme.shadow.sm).toBeDefined();
    expect(theme.motion.duration.base).toBe(200);
  });

  it("dark-mode shadows are more opaque than light-mode shadows (relies on contrast, not glow)", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    expect(dark.shadow.md.shadowOpacity as number).toBeGreaterThan(light.shadow.md.shadowOpacity as number);
  });
});
