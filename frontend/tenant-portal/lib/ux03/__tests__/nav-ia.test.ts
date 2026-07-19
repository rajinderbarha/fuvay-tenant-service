/**
 * DESIGN PHASE UX-03 — written but NOT EXECUTED (Mode B, npm install fails
 * on this machine). Run with: npm --workspace frontend/tenant-portal test
 * once a working environment is available.
 */
import { describe, it, expect } from "vitest";
import { UX03_NAV_GROUPS } from "../nav-ia";

const CANONICAL_ROLES = new Set(["tenant_owner", "staff", "technician"]);

describe("UX03_NAV_GROUPS", () => {
  it("only references canonical tenant roles", () => {
    for (const group of UX03_NAV_GROUPS) {
      for (const item of group.items) {
        for (const role of item.canonicalRoles) {
          expect(CANONICAL_ROLES.has(role)).toBe(true);
        }
      }
    }
  });

  it("never invents role names like tenant_manager or dispatcher", () => {
    const forbidden = ["tenant_manager", "tenant_readonly", "office_staff", "business_admin", "branch_manager", "dispatcher", "accountant"];
    const serialized = JSON.stringify(UX03_NAV_GROUPS);
    for (const f of forbidden) {
      expect(serialized).not.toContain(f);
    }
  });

  it("every nav item has a unique id", () => {
    const ids = UX03_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.id));
    expect(new Set(ids).size).toBe(ids.length);
  });
});
