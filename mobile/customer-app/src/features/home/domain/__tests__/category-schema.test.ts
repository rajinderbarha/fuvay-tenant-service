import { categorySummarySchema, parseCategoryList } from "../category-schema";

function category(overrides: Record<string, unknown> = {}) {
  return {
    id: "c1",
    name: "AC Repair",
    slug: "ac-repair",
    description: "Fix your air conditioner",
    category_type: "home-services",
    icon_url: "https://cdn.serviceos.in/icons/ac.png",
    banner_url: null,
    customer_flow_type: "diagnostic",
    frontend_component_key: "ac-flow",
    primary_engine_key: "hvac",
    available_offering_count: 5,
    display_order: 1,
    ...overrides,
  };
}

describe("categorySummarySchema", () => {
  it("accepts a valid category", () => {
    expect(categorySummarySchema.safeParse(category()).success).toBe(true);
  });

  it("rejects a non-https, non-relative icon URL", () => {
    expect(categorySummarySchema.safeParse(category({ icon_url: "javascript:alert(1)" })).success).toBe(false);
  });

  it("accepts a relative icon URL", () => {
    expect(categorySummarySchema.safeParse(category({ icon_url: "/static/icons/ac.png" })).success).toBe(true);
  });

  it("rejects an excessively long name", () => {
    expect(categorySummarySchema.safeParse(category({ name: "x".repeat(300) })).success).toBe(false);
  });

  it("rejects a negative offering count", () => {
    expect(categorySummarySchema.safeParse(category({ available_offering_count: -1 })).success).toBe(false);
  });

  it("rejects a missing required field", () => {
    const { id, ...rest } = category();
    expect(categorySummarySchema.safeParse(rest).success).toBe(false);
  });
});

describe("parseCategoryList", () => {
  it("keeps valid items and drops invalid ones without throwing", () => {
    const result = parseCategoryList([category(), { garbage: true }, category({ id: "c2" })]);
    expect(result.valid).toHaveLength(2);
    expect(result.droppedCount).toBe(1);
  });

  it("returns an empty valid list for entirely invalid input", () => {
    const result = parseCategoryList([{}, null, 42]);
    expect(result.valid).toHaveLength(0);
    expect(result.droppedCount).toBe(3);
  });
});
