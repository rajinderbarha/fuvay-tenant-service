import { parseSearchResponse } from "../search-schema";

const validCategory = {
  id: "cat-1",
  name: "AC Services",
  slug: "ac-services",
  description: null,
  category_type: "home_service",
  icon_url: null,
  banner_url: null,
  customer_flow_type: "diagnostic",
  frontend_component_key: null,
  primary_engine_key: null,
  available_offering_count: 3,
  display_order: 1,
};

const validOffering = {
  id: "off-1",
  name: "AC Repair",
  slug: "ac-repair",
  description: null,
  offering_class: "service",
  customer_flow_type: "diagnostic",
  primary_engine_key: null,
  pricing_model: "visit_based",
  starting_price: 199,
  visit_fee: 199,
  appointment_fee: 0,
  requires_type: false,
  requires_brand: false,
  requires_address: true,
  requires_slot: true,
  requires_photo_upload: false,
  is_available: true,
  display_order: 1,
};

describe("parseSearchResponse", () => {
  it("accepts a well-formed response with both result types", () => {
    const parsed = parseSearchResponse({ query: "ac", categories: [validCategory], offerings: [validOffering] });
    expect(parsed?.categories).toHaveLength(1);
    expect(parsed?.offerings).toHaveLength(1);
    expect(parsed?.droppedCount).toBe(0);
  });

  it("drops an individually-invalid category without failing the whole response", () => {
    const { name, ...invalidCategory } = validCategory;
    void name;
    const parsed = parseSearchResponse({ query: "ac", categories: [validCategory, invalidCategory], offerings: [] });
    expect(parsed?.categories).toHaveLength(1);
    expect(parsed?.droppedCount).toBe(1);
  });

  it("drops an individually-invalid offering without failing the whole response", () => {
    const { name, ...invalidOffering } = validOffering;
    void name;
    const parsed = parseSearchResponse({ query: "ac", categories: [], offerings: [validOffering, invalidOffering] });
    expect(parsed?.offerings).toHaveLength(1);
    expect(parsed?.droppedCount).toBe(1);
  });

  it("returns null for a malformed envelope", () => {
    expect(parseSearchResponse({ categories: "not an array" })).toBeNull();
    expect(parseSearchResponse(null)).toBeNull();
  });

  it("handles an empty-results response", () => {
    const parsed = parseSearchResponse({ query: "zzz", categories: [], offerings: [] });
    expect(parsed?.categories).toHaveLength(0);
    expect(parsed?.offerings).toHaveLength(0);
  });
});
