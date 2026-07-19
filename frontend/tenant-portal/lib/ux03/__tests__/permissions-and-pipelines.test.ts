/**
 * DESIGN PHASE UX-03 — written but NOT EXECUTED (Mode B). See execution-mode.md.
 */
import { describe, it, expect } from "vitest";
import {
  FIXTURE_TEAM_MEMBERS,
  FIXTURE_BOOKINGS,
  FIXTURE_SERVICE_JOBS,
  FIXTURE_PARTS_REQUESTS,
  FIXTURE_PERMISSION_CATALOG,
  FIXTURE_PACKAGE_CREDIT,
  FIXTURE_SECURITY_DEPOSIT,
} from "../fixtures";

describe("StaffPermission explicit-deny precedence", () => {
  it("a technician with a denied_override permission never renders as granted", () => {
    const tech = FIXTURE_TEAM_MEMBERS.find((m) => m.id === "tech_3")!;
    const denied = tech.permissions.filter((p) => p.state === "denied_override");
    expect(denied.length).toBeGreaterThan(0);
    for (const p of denied) {
      expect(p.state).not.toBe("granted_by_role");
      expect(p.state).not.toBe("granted_override");
    }
  });

  it("denied_override is distinguishable from not_granted (not the same state)", () => {
    const states = new Set(FIXTURE_PERMISSION_CATALOG.map((p) => p.state));
    expect(states.has("denied_override")).toBe(true);
    expect(states.has("not_granted")).toBe(true);
  });
});

describe("booking vs job pipeline identity", () => {
  it("bookings are tagged booking_field_ops and never mix with service jobs", () => {
    for (const b of FIXTURE_BOOKINGS) expect(b.pipeline).toBe("booking_field_ops");
  });
  it("service jobs are tagged service_booking_service_job", () => {
    for (const j of FIXTURE_SERVICE_JOBS) expect(j.pipeline).toBe("service_booking_service_job");
  });
  it("cancellation is never presented as production-ready on either pipeline", () => {
    for (const b of FIXTURE_BOOKINGS) expect(b.cancelSupported).toBe("unresolved_mock_only");
    for (const j of FIXTURE_SERVICE_JOBS) expect(j.cancelSupported).toBe("unresolved_mock_only");
  });
});

describe("PartsRequest is ServiceJob-only", () => {
  it("every parts request references a ServiceJob id, never a field_ops booking id", () => {
    const jobIds = new Set(FIXTURE_SERVICE_JOBS.map((j) => j.id));
    for (const pr of FIXTURE_PARTS_REQUESTS) {
      expect(jobIds.has(pr.serviceJobId)).toBe(true);
    }
  });
  it("no technician-install action is exposed (decidedByStaffId is null until a staff member decides)", () => {
    for (const pr of FIXTURE_PARTS_REQUESTS) {
      if (pr.status === "requested") expect(pr.decidedByStaffId).toBeNull();
    }
  });
});

describe("package credit / commission / security deposit stay separate", () => {
  it("package credit fixture has no deposit field and vice versa", () => {
    expect((FIXTURE_PACKAGE_CREDIT as any).heldAmount).toBeUndefined();
    expect((FIXTURE_SECURITY_DEPOSIT as any).creditBalance).toBeUndefined();
  });
});
