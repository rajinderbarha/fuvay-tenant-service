import { describe, expect, it } from "vitest";
import { resolveTenantPageMeta } from "./page-registry";

describe("tenant page registry", () => {
  it("uses the registered business hierarchy", () => {
    expect(resolveTenantPageMeta("/business/verification-documents")?.breadcrumbs.map((item) => item.label))
      .toEqual(["Business", "Documents"]);
  });

  it("builds readable deep breadcrumbs and never exposes an opaque record ID", () => {
    const id = "eaa56b41-773e-44da-89b8-e1f4596145fd";
    const labels = resolveTenantPageMeta(`/provider/service-invoices/${id}`)?.breadcrumbs.map((item) => item.label) ?? [];
    expect(labels).toEqual(["Provider", "Service Invoices", "Service Invoice details"]);
    expect(labels.join(" ")).not.toContain(id);
  });
});
