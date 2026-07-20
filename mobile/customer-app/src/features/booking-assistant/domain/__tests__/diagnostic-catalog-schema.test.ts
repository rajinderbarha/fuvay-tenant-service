import { parseIssueTypeList, parseServiceOptionList, parseBrandList, parseServiceTypeList } from "../diagnostic-catalog-schema";

const validIssueType = {
  issue_type_id: "it-1",
  name: "Not cooling",
  code: "NOT_COOLING",
  severity: "high",
  is_common: true,
  requires_photo: true,
  requires_description: false,
  display_order: 1,
};

const validServiceOption = {
  service_option_id: "so-1",
  name: "Gas refill",
  display_name: "Gas refill",
  code: "GAS_REFILL",
  option_group_id: null,
  is_required: false,
  is_default: false,
  display_order: 1,
};

const validBrand = { brand_id: "b-1", category_id: "cat-1", name: "LG", slug: "lg", logo_url: null, description: null, is_active: true };

const validServiceType = { type_id: "st-1", category_id: "cat-1", name: "Split AC", slug: "split-ac", description: null, icon_url: null, is_active: true };

describe("parseIssueTypeList", () => {
  it("accepts a well-formed flat array", () => {
    const result = parseIssueTypeList([validIssueType]);
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(0);
  });

  it("drops an individually-invalid item", () => {
    const { name, ...invalid } = validIssueType;
    void name;
    const result = parseIssueTypeList([validIssueType, invalid]);
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("returns null for a malformed payload", () => {
    expect(parseIssueTypeList("not an array")).toBeNull();
    expect(parseIssueTypeList(null)).toBeNull();
  });

  it("preserves the requires_photo/requires_description branching flags", () => {
    const result = parseIssueTypeList([validIssueType]);
    expect(result?.items[0].requires_photo).toBe(true);
    expect(result?.items[0].requires_description).toBe(false);
  });
});

describe("parseServiceOptionList", () => {
  it("accepts a well-formed flat array", () => {
    const result = parseServiceOptionList([validServiceOption]);
    expect(result?.items).toHaveLength(1);
  });

  it("handles an empty list", () => {
    const result = parseServiceOptionList([]);
    expect(result?.items).toHaveLength(0);
  });
});

describe("parseBrandList", () => {
  it("accepts the wrapped {brands: [...]} envelope", () => {
    const result = parseBrandList({ brands: [validBrand] });
    expect(result?.items).toHaveLength(1);
  });

  it("rejects an unsafe logo URL for that one item only", () => {
    const result = parseBrandList({ brands: [validBrand, { ...validBrand, brand_id: "b-2", logo_url: "javascript:alert(1)" }] });
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("returns null when the envelope is malformed", () => {
    expect(parseBrandList({ brands: "not an array" })).toBeNull();
  });
});

describe("parseServiceTypeList", () => {
  it("accepts the wrapped {types: [...]} envelope", () => {
    const result = parseServiceTypeList({ types: [validServiceType] });
    expect(result?.items).toHaveLength(1);
  });
});
