import { parseOfferingListPage, parseOfferingDetail } from "../offering-schema";

const validOffering = {
  id: "off-1",
  name: "AC Repair",
  slug: "ac-repair",
  description: "Fix a broken AC unit",
  offering_class: "service",
  customer_flow_type: "diagnostic",
  primary_engine_key: "home_service_booking",
  pricing_model: "visit_based",
  starting_price: 199,
  visit_fee: 199,
  appointment_fee: 0,
  requires_type: true,
  requires_brand: true,
  requires_address: true,
  requires_slot: true,
  requires_photo_upload: false,
  is_available: true,
  display_order: 1,
};

const validListPage = {
  category: { id: "cat-1", name: "AC Services", slug: "ac-services", customer_flow_type: "diagnostic" },
  items: [validOffering],
  total: 1,
  page: 1,
  page_size: 20,
};

describe("parseOfferingListPage", () => {
  it("accepts a well-formed page", () => {
    const parsed = parseOfferingListPage(validListPage);
    expect(parsed?.items).toHaveLength(1);
    expect(parsed?.droppedCount).toBe(0);
  });

  it("drops an individually-invalid item rather than failing the whole page", () => {
    const { name, ...invalidOffering } = validOffering;
    void name;
    const parsed = parseOfferingListPage({ ...validListPage, items: [validOffering, invalidOffering] });
    expect(parsed?.items).toHaveLength(1);
    expect(parsed?.droppedCount).toBe(1);
  });

  it("returns null when the envelope itself is malformed", () => {
    expect(parseOfferingListPage({ items: "not an array" })).toBeNull();
    expect(parseOfferingListPage(null)).toBeNull();
  });
});

describe("parseOfferingDetail", () => {
  const validDetail = {
    ...validOffering,
    category: { id: "cat-1", name: "AC Services", slug: "ac-services" },
    required_fields: {
      requires_type: true,
      requires_brand: true,
      requires_address: true,
      requires_slot: true,
      requires_photo_upload: false,
      requires_customer_notes: false,
    },
  };

  it("accepts a well-formed offering detail payload", () => {
    expect(parseOfferingDetail(validDetail)).toEqual(validDetail);
  });

  it("rejects a payload missing required_fields", () => {
    const { required_fields, ...withoutRequiredFields } = validDetail;
    void required_fields;
    expect(parseOfferingDetail(withoutRequiredFields)).toBeNull();
  });

  it("parses is_available even though it is not rendered as a trust signal by the UI", () => {
    expect(parseOfferingDetail({ ...validDetail, is_available: false })?.is_available).toBe(false);
  });
});
