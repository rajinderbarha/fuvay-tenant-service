import { resolveCategoryIcon, CATEGORY_ICON_FALLBACK } from "../categoryIcon";
import { resolveGlobalServiceIcon, GLOBAL_SERVICE_ICON_FALLBACK } from "../globalServiceIcon";

describe("resolveCategoryIcon", () => {
  it("gives each known category a distinct glyph", () => {
    const slugs = ["air-conditioning", "plumbing", "electrical", "painting", "pest-control", "home-cleaning"];
    const icons = slugs.map(s => resolveCategoryIcon(s));
    // The bug this guards: every category previously fell back to one
    // generic wrench, so the whole grid was visually identical.
    expect(new Set(icons).size).toBe(slugs.length);
    expect(icons).not.toContain(CATEGORY_ICON_FALLBACK);
  });

  it("falls back rather than rendering a missing glyph for an unknown slug", () => {
    expect(resolveCategoryIcon("something-new-we-added-later")).toBe(CATEGORY_ICON_FALLBACK);
    expect(resolveCategoryIcon(null)).toBe(CATEGORY_ICON_FALLBACK);
    expect(resolveCategoryIcon(undefined)).toBe(CATEGORY_ICON_FALLBACK);
  });
});

describe("resolveGlobalServiceIcon", () => {
  it("varies the icon by keyword in the admin-authored name", () => {
    expect(resolveGlobalServiceIcon("Home Inspection")).toBe("search-outline");
    expect(resolveGlobalServiceIcon("Annual Maintenance Plan")).toBe("calendar-outline");
    expect(resolveGlobalServiceIcon("Home Inspection")).not.toBe(resolveGlobalServiceIcon("Annual Maintenance Plan"));
  });

  it("keeps the generic callback glyph when nothing matches", () => {
    expect(resolveGlobalServiceIcon("Something Unrecognised")).toBe(GLOBAL_SERVICE_ICON_FALLBACK);
    expect(resolveGlobalServiceIcon(null)).toBe(GLOBAL_SERVICE_ICON_FALLBACK);
  });
});
