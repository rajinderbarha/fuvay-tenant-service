import { parseConfirmBookingResult, parseBookingDetailResponse } from "../booking-schema";

const provider = {
  tenant_id: "t-1",
  provider_name: "Acme Repairs",
  public_badges: ["Verified"],
  rating: 4.2,
  customer_visible_reason: "reason",
};

describe("parseConfirmBookingResult", () => {
  it("accepts the real first-time confirm response shape", () => {
    const parsed = parseConfirmBookingResult({
      idempotent: false,
      booking_number: "BK-20260713-000042",
      booking_id: "b-1",
      job_number: "JOB-20260713-000042",
      job_id: "j-1",
      status: "pending_assignment",
      booking_status: "confirmed",
      confirmation_id: "c-1",
      selected_provider_tenant_id: "t-1",
      selected_price_option: "mid",
      selected_price_amount: 690,
      payment_mode: "customer_pays_provider_directly",
    });
    expect(parsed?.booking_number).toBe("BK-20260713-000042");
    expect(parsed?.idempotent).toBe(false);
  });

  it("accepts the real, smaller idempotent-retry response shape", () => {
    const parsed = parseConfirmBookingResult({
      idempotent: true,
      booking_number: "BK-20260713-000042",
      booking_id: "b-1",
      confirmation_id: "c-1",
    });
    expect(parsed?.idempotent).toBe(true);
    expect(parsed?.job_number).toBeUndefined();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseConfirmBookingResult(null)).toBeNull();
    expect(parseConfirmBookingResult({})).toBeNull();
    expect(parseConfirmBookingResult({ idempotent: false, booking_number: "x" })).toBeNull();
  });
});

describe("parseBookingDetailResponse", () => {
  const validBooking = {
    id: "b-1",
    booking_number: "BK-20260713-000042",
    draft_id: "d-1",
    customer_name: "Asha",
    customer_phone: "9999999999",
    city: "Pune",
    zipcode: "411001",
    address_snapshot: {
      address_line_1: "12 MG Road",
      address_line_2: null,
      landmark: null,
      city: "Pune",
      state: "MH",
      zipcode: "411001",
      country: "IN",
      name: "Asha",
      phone: "9999999999",
    },
    preferred_date: null,
    preferred_time_window: "Morning",
    price_snapshot: { currency: "INR", selected_price_option: "mid", selected_price_amount: 690, payment_mode: "customer_pays_provider_directly" },
    provider_snapshot: provider,
    issue_summary: "Not cooling",
    status: "pending_assignment",
    failure_reason: null,
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
    job: { id: "j-1", job_number: "JOB-20260713-000042", status: "pending_assignment" },
  };

  it("parses a real, found booking", () => {
    const result = parseBookingDetailResponse(validBooking);
    expect(result.kind).toBe("found");
    if (result.kind === "found") {
      expect(result.booking.booking_number).toBe("BK-20260713-000042");
    }
  });

  it("strips internal_score/matching_score_snapshot from the raw, unstripped provider_snapshot", () => {
    const result = parseBookingDetailResponse({
      ...validBooking,
      provider_snapshot: { ...provider, internal_score: 87.5, matching_score_snapshot: { distance: 60 } },
    });
    expect(result.kind).toBe("found");
    if (result.kind === "found") {
      expect(result.booking.provider_snapshot).not.toBeNull();
      expect(Object.keys(result.booking.provider_snapshot as object).sort()).toEqual([
        "customer_visible_reason",
        "provider_name",
        "public_badges",
        "rating",
        "tenant_id",
      ]);
    }
  });

  it("parses the real 200-with-error-body not-found shape", () => {
    const result = parseBookingDetailResponse({ error: "FINAL_BOOKING_NOT_FOUND" });
    expect(result).toEqual({ kind: "error", code: "FINAL_BOOKING_NOT_FOUND" });
  });

  it("parses the real 200-with-error-body access-denied shape", () => {
    const result = parseBookingDetailResponse({ error: "FINAL_ACCESS_DENIED" });
    expect(result).toEqual({ kind: "error", code: "FINAL_ACCESS_DENIED" });
  });

  it("fails closed on a malformed payload without throwing", () => {
    expect(parseBookingDetailResponse(null)).toEqual({ kind: "invalid" });
    expect(parseBookingDetailResponse({})).toEqual({ kind: "invalid" });
  });
});
