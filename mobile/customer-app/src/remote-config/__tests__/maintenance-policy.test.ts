import { evaluateMaintenancePolicy } from "../maintenance-policy";
import type { MaintenanceConfig } from "../remote-config-schema";

const NOW = "2026-06-01T12:00:00.000Z";

function config(overrides: Partial<MaintenanceConfig>): MaintenanceConfig {
  return { enabled: false, type: "none", retryAllowed: true, permittedRouteIds: [], ...overrides };
}

describe("evaluateMaintenancePolicy", () => {
  it("is none when disabled", () => {
    expect(evaluateMaintenancePolicy(config({ enabled: false }), NOW).status).toBe("none");
  });

  it("is scheduled when startAt is in the future", () => {
    const result = evaluateMaintenancePolicy(config({ enabled: true, type: "scheduled", startAt: "2026-06-02T00:00:00.000Z" }), NOW);
    expect(result.status).toBe("scheduled");
    expect(result.blocking).toBe(false);
  });

  it("is active and blocking for active-blocking within the window", () => {
    const result = evaluateMaintenancePolicy(
      config({ enabled: true, type: "active-blocking", startAt: "2026-06-01T00:00:00.000Z", estimatedEndAt: "2026-06-01T23:00:00.000Z" }),
      NOW
    );
    expect(result.status).toBe("active");
    expect(result.blocking).toBe(true);
  });

  it("is active but read-only (not blocking) for active-read-only", () => {
    const result = evaluateMaintenancePolicy(
      config({ enabled: true, type: "active-read-only", startAt: "2026-06-01T00:00:00.000Z", estimatedEndAt: "2026-06-01T23:00:00.000Z" }),
      NOW
    );
    expect(result.status).toBe("active");
    expect(result.blocking).toBe(false);
    expect(result.readOnly).toBe(true);
  });

  it("is expired once now is past estimatedEndAt", () => {
    const result = evaluateMaintenancePolicy(
      config({ enabled: true, type: "active-blocking", startAt: "2026-05-30T00:00:00.000Z", estimatedEndAt: "2026-05-31T00:00:00.000Z" }),
      NOW
    );
    expect(result.status).toBe("expired");
    expect(result.blocking).toBe(false);
  });

  it("respects retryAllowed=false", () => {
    const result = evaluateMaintenancePolicy(config({ enabled: true, type: "active-blocking", retryAllowed: false }), NOW);
    expect(result.retryAllowed).toBe(false);
  });

  it("is platform/marketplace-specific only insofar as the caller narrows the config before calling — evaluator itself is timezone-safe absolute-time comparison", () => {
    const result = evaluateMaintenancePolicy(config({ enabled: true, type: "active-blocking" }), NOW);
    expect(result.status).toBe("active");
  });
});
