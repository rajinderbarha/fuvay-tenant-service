import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import HomeServicesCatalogNav from "./HomeServicesCatalogNav";
import { BLUEPRINT_SETUP_STEPS, CATALOG_SETUP_STEPS } from "./catalog-setup-sequence";

afterEach(cleanup);

describe("guided catalog setup", () => {
  it("orders libraries before per-service configuration", () => {
    expect(CATALOG_SETUP_STEPS.map(step => step.key)).toEqual([
      "categories", "groups", "services", "types-brands", "checklists", "workspace",
    ]);
    expect(BLUEPRINT_SETUP_STEPS.map(step => step.key)).toEqual([
      "overview", "workflow", "dimensions", "problems", "checklist", "tenant_rules", "preview",
    ]);
  });

  it.each(CATALOG_SETUP_STEPS)("shows prerequisites and valid neighbors for $label", step => {
    render(<HomeServicesCatalogNav active={step.key} />);
    const current = screen.getAllByRole("link").filter(link => link.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(current[0].getAttribute("href")).toBe(step.href);
    expect(screen.getByText(`Before continuing: ${step.done}`)).toBeTruthy();
    expect(screen.getByText(/Navigation does not indicate completion/)).toBeTruthy();
    const index = CATALOG_SETUP_STEPS.indexOf(step);
    if (index > 0) expect(screen.getByRole("link", { name: `← Back: ${CATALOG_SETUP_STEPS[index - 1].label}` }).getAttribute("href")).toBe(CATALOG_SETUP_STEPS[index - 1].href);
    if (index < 5) expect(screen.getByRole("link", { name: `Next: ${CATALOG_SETUP_STEPS[index + 1].label} →` }).getAttribute("href")).toBe(CATALOG_SETUP_STEPS[index + 1].href);
  });
});
