import { resolveGlobalServiceAccent, GLOBAL_SERVICE_ACCENT_PALETTE } from "../globalServiceAccent";

const LIVE_SERVICES = [
  "Web Development",
  "Mobile App Dev",
  "Software Development",
  "Blockchain Dev",
  "AI & ML",
  "Data Analyst",
];

describe("resolveGlobalServiceAccent", () => {
  it("gives every live service a distinct colour", () => {
    // The whole point of the section's redesign: each card carries its own
    // identity colour, so two cards sharing one would read as a bug.
    const colours = LIVE_SERVICES.map(n => resolveGlobalServiceAccent(n).background);
    expect(new Set(colours).size).toBe(LIVE_SERVICES.length);
  });

  it("is stable for the same name", () => {
    expect(resolveGlobalServiceAccent("Web Development").background)
      .toBe(resolveGlobalServiceAccent("Web Development").background);
  });

  it("matches on keyword regardless of casing", () => {
    // Global Services are free-text admin rows -- the live catalog already
    // contains "Blockchain Dev" where an earlier row used "Blockchain dev".
    expect(resolveGlobalServiceAccent("blockchain dev").background)
      .toBe(resolveGlobalServiceAccent("Blockchain Dev").background);
  });

  it("still returns a palette colour for an unrecognised service", () => {
    // A newly-added offering must look intentional, not fall back to grey.
    const accent = resolveGlobalServiceAccent("Drone Photography");
    expect(GLOBAL_SERVICE_ACCENT_PALETTE).toContain(accent.background);
  });

  it("handles a missing name without throwing", () => {
    expect(GLOBAL_SERVICE_ACCENT_PALETTE).toContain(resolveGlobalServiceAccent(null).background);
    expect(GLOBAL_SERVICE_ACCENT_PALETTE).toContain(resolveGlobalServiceAccent(undefined).background);
  });

  it("uses white foregrounds, since every card background is a saturated brand colour", () => {
    const a = resolveGlobalServiceAccent("Web Development");
    expect(a.onBackground).toBe("#FFFFFF");
    expect(a.onBackgroundMuted).toMatch(/^rgba\(255,255,255/);
  });
});
