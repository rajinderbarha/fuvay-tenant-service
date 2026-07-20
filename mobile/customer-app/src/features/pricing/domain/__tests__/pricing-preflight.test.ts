import { evaluatePricingPreflight } from "../pricing-preflight";
import type { ValidatedBookingDraft } from "../../../booking-draft/domain/draft-schema";

const baseDraft: ValidatedBookingDraft = {
  id: "draft-1",
  customer_id: "cust-1",
  guest_session_id: null,
  ai_session_id: null,
  category_id: "cat-1",
  offering_id: "off-1",
  selected_tenant_id: "t-1",
  status: "provider_matched",
  customer_name: null,
  customer_phone: null,
  address_id: "addr-1",
  city: "Pune",
  zipcode: "411001",
  issue_summary: null,
  offering_type_id: null,
  brand_id: null,
  photo_urls: [],
  preferred_date: null,
  preferred_time_window: null,
  serviceability_status: "serviceable",
  price_status: null,
  provider_match_status: "matched",
  failure_code: null,
  failure_message: null,
  expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  created_at: null,
  updated_at: null,
};

describe("evaluatePricingPreflight", () => {
  it("is ready when all real preconditions are met", () => {
    expect(evaluatePricingPreflight(baseDraft)).toEqual({ ready: true });
  });

  it("fails closed when the draft is missing entirely", () => {
    expect(evaluatePricingPreflight(null)).toEqual({ ready: false, reasonKey: "pricing.preflight.draftMissing" });
    expect(evaluatePricingPreflight(undefined)).toEqual({ ready: false, reasonKey: "pricing.preflight.draftMissing" });
  });

  it("fails when the draft has passed its real expiry", () => {
    const expired = { ...baseDraft, expires_at: new Date(Date.now() - 1000).toISOString() };
    expect(evaluatePricingPreflight(expired)).toEqual({ ready: false, reasonKey: "pricing.preflight.draftExpired" });
  });

  it("fails when no address is selected", () => {
    expect(evaluatePricingPreflight({ ...baseDraft, address_id: null })).toEqual({ ready: false, reasonKey: "pricing.preflight.addressMissing" });
  });

  it("fails when serviceability was never confirmed", () => {
    expect(evaluatePricingPreflight({ ...baseDraft, serviceability_status: "not_serviceable" })).toEqual({
      ready: false,
      reasonKey: "pricing.preflight.notServiceable",
    });
  });

  it("fails when no provider has been matched", () => {
    expect(evaluatePricingPreflight({ ...baseDraft, provider_match_status: "pending", selected_tenant_id: null })).toEqual({
      ready: false,
      reasonKey: "pricing.preflight.providerNotMatched",
    });
  });
});
