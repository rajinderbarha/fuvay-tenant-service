import { deriveRole, permissionsFor, hasPermission, KNOWN_PERMISSION_KEYS } from "../permissions";
import type { StaffUser } from "../../api";

const baseUser: StaffUser = {
  id: "staff_1", full_name: "Ravi Kumar", specialisations: ["ac_repair"], status: "active",
};

describe("deriveRole (fail-closed)", () => {
  it("defaults an unlabelled StaffUser to technician (no live role field on the backend yet)", () => {
    expect(deriveRole(baseUser)).toBe("technician");
  });

  it("only elevates to staff on an explicit role:'staff' value", () => {
    expect(deriveRole({ ...baseUser, role: "staff" } as any)).toBe("staff");
  });

  it("never invents a role outside the canonical staff|technician set", () => {
    const role = deriveRole({ ...baseUser, role: "dispatcher" } as any);
    expect(["staff", "technician"]).toContain(role);
  });
});

describe("permissionsFor", () => {
  it("denies every known permission for technician", () => {
    const perms = permissionsFor("technician", "tenant_1");
    expect(perms).toHaveLength(KNOWN_PERMISSION_KEYS.length);
    expect(perms.every(p => p.granted === false)).toBe(true);
  });

  it("tags staff permissions as MOCK_DESIGN_ONLY (no live StaffPermission endpoint yet), never granted for real", () => {
    const perms = permissionsFor("staff", "tenant_1");
    expect(perms.every(p => p.granted === false)).toBe(true);
    expect(perms.every(p => p.reason?.includes("MOCK_DESIGN_ONLY"))).toBe(true);
  });

  it("scopes every permission to the given tenant", () => {
    const perms = permissionsFor("staff", "tenant_42");
    expect(perms.every(p => p.scopeTenantId === "tenant_42")).toBe(true);
  });
});

describe("hasPermission (explicit deny overrides grant)", () => {
  it("returns false when not present in the list", () => {
    expect(hasPermission([], "parts_request:approve")).toBe(false);
  });

  it("returns true only when granted and not explicitly denied", () => {
    const perms = [{ permissionKey: "parts_request:approve", granted: true, explicitDeny: false, scopeTenantId: "t1", reason: null }];
    expect(hasPermission(perms, "parts_request:approve")).toBe(true);
  });

  it("explicit deny overrides a grant", () => {
    const perms = [{ permissionKey: "parts_request:approve", granted: true, explicitDeny: true, scopeTenantId: "t1", reason: "revoked" }];
    expect(hasPermission(perms, "parts_request:approve")).toBe(false);
  });
});
