import { buildPublicHeaders, buildAuthenticatedHeaders, withConcurrencyFields } from "../requestHeaders";

describe("buildPublicHeaders", () => {
  it("includes a generated X-Request-ID and never an Authorization header", () => {
    const headers = buildPublicHeaders();
    expect(headers["X-Request-ID"]).toMatch(/^req_/);
    expect(headers.Authorization).toBeUndefined();
  });
});

describe("buildAuthenticatedHeaders", () => {
  it("attaches Authorization: Bearer <token>", () => {
    const headers = buildAuthenticatedHeaders("tok123");
    expect(headers.Authorization).toBe("Bearer tok123");
  });

  it("attaches X-Idempotency-Key only when provided", () => {
    const withKey = buildAuthenticatedHeaders("tok", "idem-1");
    expect(withKey["X-Idempotency-Key"]).toBe("idem-1");
    const withoutKey = buildAuthenticatedHeaders("tok");
    expect(withoutKey["X-Idempotency-Key"]).toBeUndefined();
  });
});

describe("withConcurrencyFields", () => {
  it("merges expected_version from entityVersion into the body (real backend convention)", () => {
    const body = withConcurrencyFields({ note: "x" }, { entityVersion: 3 });
    expect(body).toEqual({ note: "x", expected_version: 3 });
  });

  it("merges quote_id when provided", () => {
    const body = withConcurrencyFields({}, { quoteVersion: 2, quoteId: "q1" });
    expect(body).toEqual({ expected_version: 2, quote_id: "q1" });
  });

  it("returns the body unchanged when no concurrency contract is given", () => {
    const body = { a: 1 };
    expect(withConcurrencyFields(body)).toBe(body);
  });
});
