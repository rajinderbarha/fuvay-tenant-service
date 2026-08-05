import { mapHttpError, DomainError, UnknownStatusError, ContractValidationError } from "../errors";

describe("structured error architecture", () => {
  it("maps a 401 to AUTH_REQUIRED and a 403 to FORBIDDEN", () => {
    expect(mapHttpError(401, "diag").category).toBe("AUTH_REQUIRED");
    expect(mapHttpError(403, "diag").category).toBe("FORBIDDEN");
  });

  it("maps any 5xx to BACKEND_UNAVAILABLE", () => {
    expect(mapHttpError(500, "diag").category).toBe("BACKEND_UNAVAILABLE");
    expect(mapHttpError(503, "diag").category).toBe("BACKEND_UNAVAILABLE");
  });

  it("maps a missing status (network failure) to NETWORK_UNAVAILABLE", () => {
    expect(mapHttpError(undefined, "diag").category).toBe("NETWORK_UNAVAILABLE");
  });

  it("falls back to UNKNOWN for an unmapped 4xx", () => {
    expect(mapHttpError(418, "diag").category).toBe("UNKNOWN");
  });

  it("never exposes diagnostic detail as the customer-facing messageKey", () => {
    const err = new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "raw stack trace or SQL detail" });
    expect(err.messageKey).not.toContain("raw stack trace");
    expect(err.messageKey).toBe("error.validation_failure");
  });

  it("UnknownStatusError carries the offending field/value as safe telemetry metadata", () => {
    const err = new UnknownStatusError("status", "levitating", "job-1");
    expect(err.telemetryMeta).toEqual({ field: "status", value: "levitating" });
    expect(err.category).toBe("CONTRACT_MISMATCH");
  });

  it("ContractValidationError aggregates issues into one diagnostic", () => {
    const err = new ContractValidationError("ServiceJobDto", ["id: required", "status: required"]);
    expect(err.diagnostic).toContain("id: required");
    expect(err.diagnostic).toContain("status: required");
  });
});
