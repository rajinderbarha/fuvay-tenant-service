/**
 * UX-06 Round 4 — tests for the real booking-submission contract layer
 * (homeServiceDraftApi / bookingConfirmApi), added after live-verifying the
 * real endpoints this round (see docs/design/ux-06-customer-app/
 * canonical-booking-contract.md, seed-before-after-report.md).
 */

describe("homeServiceDraftApi / bookingConfirmApi — request shape enforcement", () => {
  const realFetch = global.fetch;
  afterEach(() => { global.fetch = realFetch; jest.restoreAllMocks(); jest.resetModules(); });

  function mockFetchCapturing() {
    const calls: { url: string; opts: any }[] = [];
    global.fetch = jest.fn(async (url: any, opts: any) => {
      calls.push({ url: String(url), opts });
      return { ok: true, json: async () => ({ data: { id: "draft-1", status: "created" } }) } as Response;
    }) as unknown as typeof fetch;
    return calls;
  }

  it("start() sends only category_slug/offering_slug/ai_session_id -- never a raw price or tenant field", async () => {
    const calls = mockFetchCapturing();
    const { homeServiceDraftApi } = require("../api");
    await homeServiceDraftApi.start("home_services", "ac_repair", "session-1");
    const body = JSON.parse(calls[0].opts.body);
    expect(Object.keys(body).sort()).toEqual(["ai_session_id", "category_slug", "offering_slug"].sort());
    expect(body).not.toHaveProperty("price");
    expect(body).not.toHaveProperty("tenant_id");
  });

  it("bookingConfirmApi.confirmHomeServiceBooking sends a real Idempotency-Key header to the REAL customer confirm route, never a client price", async () => {
    // UX-06 Round 5 correction: the real, correct route is
    // /v1/customer/home-services/booking-drafts/{id}/confirm (calls
    // mark_ready_for_confirmation() then finalize()) -- NOT
    // /v1/customer/confirm/home-service-booking/{id} (finalize() only,
    // requires a precondition only the first route establishes). See
    // bargain-contract-audit.md.
    const calls = mockFetchCapturing();
    const { bookingConfirmApi } = require("../api");
    await bookingConfirmApi.confirmHomeServiceBooking("draft-123", "draft-123");
    expect(calls[0].url).toContain("/v1/customer/home-services/booking-drafts/draft-123/confirm");
    expect(calls[0].opts.headers["Idempotency-Key"]).toBe("draft-123");
    // confirm_draft takes no body params -- nothing client-supplied at all,
    // so there is no price/tenant field to check for absence of a body.
    expect(calls[0].opts.body).toBeUndefined();
  });

  it("duplicate submission uses the SAME idempotency key on retry, not a new one, for a given draft", async () => {
    const calls = mockFetchCapturing();
    const { bookingConfirmApi } = require("../api");
    await bookingConfirmApi.confirmHomeServiceBooking("draft-999", "draft-999");
    await bookingConfirmApi.confirmHomeServiceBooking("draft-999", "draft-999");
    expect(calls).toHaveLength(2);
    expect(calls[0].opts.headers["Idempotency-Key"]).toBe(calls[1].opts.headers["Idempotency-Key"]);
  });

  it("priceEstimate/serviceabilityCheck are GET-free POSTs with no request body price field (server-authoritative only)", async () => {
    const calls = mockFetchCapturing();
    const { homeServiceDraftApi } = require("../api");
    await homeServiceDraftApi.serviceabilityCheck("draft-1");
    await homeServiceDraftApi.priceEstimate("draft-1");
    for (const call of calls) {
      expect(call.opts.method).toBe("POST");
      expect(call.opts.body).toBeUndefined();
    }
  });
});
