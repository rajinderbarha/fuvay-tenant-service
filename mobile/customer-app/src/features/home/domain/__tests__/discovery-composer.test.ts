import { composeCategorySections } from "../discovery-composer";
import type { ValidatedCategorySummary } from "../category-schema";

function category(overrides: Partial<ValidatedCategorySummary> = {}): ValidatedCategorySummary {
  return {
    id: "c1",
    name: "AC Repair",
    slug: "ac-repair",
    description: null,
    category_type: "home-services",
    icon_url: null,
    banner_url: null,
    customer_flow_type: "diagnostic",
    frontend_component_key: null,
    primary_engine_key: null,
    available_offering_count: 3,
    display_order: 1,
    ...overrides,
  };
}

describe("composeCategorySections", () => {
  it("maps categories into HomeCategoryItem shape", () => {
    const result = composeCategorySections([category()]);
    expect(result.items[0]).toMatchObject({ id: "c1", name: "AC Repair", offeringCount: 3 });
  });

  it("deduplicates by id, keeping the first occurrence", () => {
    const result = composeCategorySections([category({ id: "c1", name: "First" }), category({ id: "c1", name: "Second" })]);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].name).toBe("First");
    expect(result.droppedDuplicateCount).toBe(1);
  });

  it("sorts by display_order, then name as a tie-breaker", () => {
    const result = composeCategorySections([
      category({ id: "c2", name: "Zebra", display_order: 1 }),
      category({ id: "c1", name: "Apple", display_order: 1 }),
      category({ id: "c3", name: "Anything", display_order: 0 }),
    ]);
    expect(result.items.map((item) => item.id)).toEqual(["c3", "c1", "c2"]);
  });

  it("produces the same order across repeated calls (no random ordering)", () => {
    const input = [category({ id: "c1", display_order: 2 }), category({ id: "c2", display_order: 1 })];
    const first = composeCategorySections(input).items.map((i) => i.id);
    const second = composeCategorySections(input).items.map((i) => i.id);
    expect(first).toEqual(second);
  });

  it("caps the result at 12 items", () => {
    const many = Array.from({ length: 20 }, (_, i) => category({ id: `c${i}`, display_order: i }));
    const result = composeCategorySections(many);
    expect(result.items).toHaveLength(12);
  });
});
