import { describe, it, expect } from "vitest";
import { UX02_NAV_GROUPS } from "../../lib/ux02/nav-ia";

const CANONICAL_ROLES = ["super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"];

describe("UX02_NAV_GROUPS", () => {
  it("only references canonical admin roles", () => {
    for (const group of UX02_NAV_GROUPS) {
      for (const item of group.items) {
        for (const role of item.canonicalRoles) {
          expect(CANONICAL_ROLES).toContain(role);
        }
      }
    }
  });

  it("every item has a unique id", () => {
    const ids = UX02_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.id));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every item declares a readiness state", () => {
    for (const group of UX02_NAV_GROUPS) {
      for (const item of group.items) {
        expect(item.readiness).toBeTruthy();
      }
    }
  });
});
