import { describe, it, expect } from "vitest";
import { colorVar, chartPalette } from "../tokens/color";
import { typeScale } from "../tokens/typography";
import { space, radius, breakpoints } from "../tokens/spacing";
import { statusRegistry } from "../tokens/motion";

describe("design tokens", () => {
  it("exposes CSS var references for semantic colors, never raw hex", () => {
    expect(colorVar.brand).toBe("var(--brand)");
    expect(colorVar.danger).toMatch(/^var\(--/);
  });

  it("provides a light and dark chart palette of equal length", () => {
    expect(chartPalette.light.length).toBe(chartPalette.dark.length);
    expect(chartPalette.light.length).toBeGreaterThanOrEqual(6);
  });

  it("defines the full type scale used by the spec", () => {
    expect(Object.keys(typeScale)).toEqual(
      expect.arrayContaining(["display", "pageTitle", "body", "label", "tableHeader", "numeric", "code"])
    );
  });

  it("has a coherent spacing/radius/breakpoint scale", () => {
    expect(space[4]).toBe("1rem");
    expect(radius.full).toBe("9999px");
    expect(breakpoints.md).toBe("768px");
  });

  it("registers a safe set of known statuses", () => {
    expect(statusRegistry.active.tone).toBe("success");
    expect(statusRegistry.cancelled.tone).toBe("danger");
  });
});
