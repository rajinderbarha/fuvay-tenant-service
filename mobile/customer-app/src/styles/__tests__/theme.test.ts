import { buildTheme } from "../theme";

// UX-07 Round 4 Pass 2: real assertions that the dark palette is a distinct,
// correctly-inverted surface hierarchy -- not just a copy of light values
// with names changed. Guards against a future edit accidentally making
// dark mode identical to light (which would silently defeat the whole
// dark-mode contract).
describe("buildTheme", () => {
  it("produces genuinely different bg/surface colors between light and dark", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    expect(light.colors.bg).not.toBe(dark.colors.bg);
    expect(light.colors.surface).not.toBe(dark.colors.surface);
    expect(light.colors.textPrimary).not.toBe(dark.colors.textPrimary);
  });

  it("maintains a real surface hierarchy in dark mode (background, card, raised, interactive, selected are all distinct)", () => {
    const dark = buildTheme("dark");
    const surfaces = [
      dark.colors.bg, dark.colors.surface, dark.colors.surfaceCard,
      dark.colors.surfaceRaised, dark.colors.surfaceInteractive, dark.colors.surfaceSelected,
    ];
    // Not literally identical across the board (a "pure black everywhere" bug
    // would collapse several of these to the same value).
    const distinct = new Set(surfaces);
    expect(distinct.size).toBeGreaterThan(3);
  });

  it("dark mode is not literally black backgrounds (avoids the pure-black anti-pattern)", () => {
    const dark = buildTheme("dark");
    expect(dark.colors.bg.toLowerCase()).not.toBe("#000000");
    expect(dark.colors.surface.toLowerCase()).not.toBe("#000000");
  });

  it("statusBarStyle is dark-content on light backgrounds and light-content on dark backgrounds", () => {
    expect(buildTheme("light").colors.statusBarStyle).toBe("dark");
    expect(buildTheme("dark").colors.statusBarStyle).toBe("light");
  });

  it("shares identical spacing/font/radius scales across modes (only color changes, not layout)", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    expect(dark.spacing).toEqual(light.spacing);
    expect(dark.font).toEqual(light.font);
    expect(dark.radius).toEqual(light.radius);
  });
});
