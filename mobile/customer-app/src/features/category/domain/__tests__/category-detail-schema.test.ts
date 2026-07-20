import { parseCategoryDetail } from "../category-detail-schema";

const validPayload = {
  id: "cat-1",
  name: "AC Services",
  slug: "ac-services",
  description: "Repair, service and installation",
  category_type: "home_service",
  icon_url: "https://cdn.example.com/icon.png",
  banner_url: null,
  customer_flow_type: "diagnostic",
  frontend_component_key: "DiagnosticFlow",
  primary_engine_key: "home_service_booking",
  available_offering_count: 4,
  display_order: 1,
  required_steps: ["address", "slot"],
  optional_steps: [],
};

describe("parseCategoryDetail", () => {
  it("accepts a well-formed real-shaped payload", () => {
    expect(parseCategoryDetail(validPayload)).toEqual(validPayload);
  });

  it("rejects a payload missing a required field", () => {
    const { id, ...withoutId } = validPayload;
    void id;
    expect(parseCategoryDetail(withoutId)).toBeNull();
  });

  it("rejects an unsafe (non-https, non-relative) image URL", () => {
    expect(parseCategoryDetail({ ...validPayload, icon_url: "javascript:alert(1)" })).toBeNull();
  });

  it("accepts a relative image URL", () => {
    expect(parseCategoryDetail({ ...validPayload, icon_url: "/static/icon.png" })?.icon_url).toBe("/static/icon.png");
  });

  it("rejects a completely malformed payload without throwing", () => {
    expect(parseCategoryDetail(null)).toBeNull();
    expect(parseCategoryDetail("not an object")).toBeNull();
    expect(parseCategoryDetail(undefined)).toBeNull();
  });
});
