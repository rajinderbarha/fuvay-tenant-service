import { describe, expect, it } from "vitest";
import { resolvePageMeta } from "./page-registry";

describe("admin page registry", () => {
  it("preserves registered hierarchy for deep detail routes without exposing IDs", () => {
    const meta = resolvePageMeta("/admin/finance/claims/eaa56b41-773e-44da-89b8-e1f4596145fd");
    expect(meta?.breadcrumbs.map((item) => item.label)).toEqual([
      "Finance",
      "Claims",
      "Claim details",
    ]);
  });

  it("creates a useful label for a live route that has no explicit registry entry", () => {
    expect(resolvePageMeta("/admin/workflow-templates")?.breadcrumbs.at(-1)?.label)
      .toBe("Workflow Templates");
  });
});
