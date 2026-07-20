import { parseBookingDraft, parseCancelResponse, parseLinkPhotoResponse, isTerminalDraftStatus, isPastExpiry } from "../draft-schema";

const validDraft = {
  id: "draft-1",
  customer_id: "cust-1",
  guest_session_id: null,
  ai_session_id: null,
  category_id: "cat-1",
  offering_id: "svc-1",
  selected_tenant_id: null,
  status: "draft",
  customer_name: null,
  customer_phone: null,
  address_id: null,
  city: null,
  zipcode: null,
  issue_summary: null,
  offering_type_id: null,
  brand_id: null,
  photo_urls: [],
  preferred_date: null,
  preferred_time_window: null,
  serviceability_status: "pending",
  price_status: "pending",
  provider_match_status: "pending",
  failure_code: null,
  failure_message: null,
  expires_at: "2099-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  offering_name: "AC Repair",
  offering_slug: "ac-repair",
  category_name: "AC Services",
  category_slug: "ac-services",
  required_fields: ["issue_summary", "city"],
};

describe("parseBookingDraft", () => {
  it("accepts a well-formed real-shaped draft", () => {
    expect(parseBookingDraft(validDraft)).toEqual(validDraft);
  });

  it("rejects a payload missing a required field", () => {
    const { status, ...withoutStatus } = validDraft;
    void status;
    expect(parseBookingDraft(withoutStatus)).toBeNull();
  });

  it("accepts a draft without the optional enrichment fields (e.g. cancel's short response never has them)", () => {
    const { offering_name, offering_slug, category_name, category_slug, required_fields, ...bare } = validDraft;
    void offering_name;
    void offering_slug;
    void category_name;
    void category_slug;
    void required_fields;
    expect(parseBookingDraft(bare)).not.toBeNull();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseBookingDraft(null)).toBeNull();
    expect(parseBookingDraft("not an object")).toBeNull();
  });
});

describe("isTerminalDraftStatus", () => {
  it("classifies confirmed/expired/cancelled/failed as terminal", () => {
    expect(isTerminalDraftStatus("confirmed")).toBe(true);
    expect(isTerminalDraftStatus("expired")).toBe(true);
    expect(isTerminalDraftStatus("cancelled")).toBe(true);
    expect(isTerminalDraftStatus("failed")).toBe(true);
  });

  it("classifies in-progress statuses as non-terminal", () => {
    expect(isTerminalDraftStatus("draft")).toBe(false);
    expect(isTerminalDraftStatus("collecting_details")).toBe(false);
    expect(isTerminalDraftStatus("ready_for_confirmation")).toBe(false);
  });
});

describe("isPastExpiry", () => {
  it("returns false when expires_at is in the future", () => {
    const draft = parseBookingDraft(validDraft)!;
    expect(isPastExpiry(draft, new Date("2026-06-01T00:00:00Z").getTime())).toBe(false);
  });

  it("returns true when now is past expires_at, even if status has not flipped yet", () => {
    const draft = parseBookingDraft({ ...validDraft, expires_at: "2020-01-01T00:00:00Z" })!;
    expect(isPastExpiry(draft, new Date("2026-01-01T00:00:00Z").getTime())).toBe(true);
  });

  it("returns false when expires_at is null", () => {
    const draft = parseBookingDraft({ ...validDraft, expires_at: null })!;
    expect(isPastExpiry(draft)).toBe(false);
  });
});

describe("parseCancelResponse", () => {
  it("accepts the real short cancel response shape", () => {
    expect(parseCancelResponse({ draft_status: "cancelled", message: "Booking draft cancelled." })).toEqual({
      draft_status: "cancelled",
      message: "Booking draft cancelled.",
    });
  });

  it("rejects a malformed response", () => {
    expect(parseCancelResponse({ draft_status: "cancelled" })).toBeNull();
  });
});

describe("parseLinkPhotoResponse", () => {
  it("accepts the real photo-link response shape", () => {
    expect(parseLinkPhotoResponse({ photo_urls: ["/v1/media/x/view"], draft_status: "draft" })).toEqual({
      photo_urls: ["/v1/media/x/view"],
      draft_status: "draft",
    });
  });
});
