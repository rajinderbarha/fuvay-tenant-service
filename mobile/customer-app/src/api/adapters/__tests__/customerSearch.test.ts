import { parseCustomerSearchDto, adaptCustomerSearch } from "../customerSearch";

const BOOKABLE = "59d8f3aa-932d-429e-93bd-8d4f2ed615c3";
const NOT_BOOKABLE = "405cd796-9c97-4465-8a17-e7137e34d268";

function dto(over: Record<string, unknown> = {}) {
  return parseCustomerSearchDto({
    query: "a", categories: [], offerings: [], ...over,
  });
}

describe("adaptCustomerSearch", () => {
  it("flags results whose category is not bookable at this ZIP", () => {
    // The search endpoint has NO zipcode parameter, so it can return
    // something the customer cannot book where they are. Marking it is what
    // stops a tap dead-ending several booking steps later at
    // "no provider available".
    const out = adaptCustomerSearch(
      dto({
        categories: [
          { id: BOOKABLE, name: "Air Conditioning", slug: "air-conditioning" },
          { id: NOT_BOOKABLE, name: "Plumbing", slug: "plumbing" },
        ],
      }),
      new Set([BOOKABLE]),
    );
    const byName = Object.fromEntries(out.results.map(r => [r.name, r.bookableHere]));
    expect(byName["Air Conditioning"]).toBe(true);
    expect(byName["Plumbing"]).toBe(false);
  });

  it("resolves an offering's availability through its parent category", () => {
    const out = adaptCustomerSearch(
      dto({
        offerings: [
          { id: "s1", name: "AC Gas Refilling", starting_price: 299, category_id: BOOKABLE },
          { id: "s2", name: "Pipe Repair", starting_price: 60, category_id: NOT_BOOKABLE },
        ],
      }),
      new Set([BOOKABLE]),
    );
    const byName = Object.fromEntries(out.results.map(r => [r.name, r.bookableHere]));
    expect(byName["AC Gas Refilling"]).toBe(true);
    expect(byName["Pipe Repair"]).toBe(false);
  });

  it("treats an offering with no parent category as not bookable", () => {
    // Rather than optimistically assuming availability -- an unbookable tap
    // is worse than an honestly-greyed row.
    const out = adaptCustomerSearch(
      dto({ offerings: [{ id: "s3", name: "Orphan Service" }] }),
      new Set([BOOKABLE]),
    );
    expect(out.results[0].bookableHere).toBe(false);
  });

  it("ranks bookable before unavailable, and categories before services", () => {
    const out = adaptCustomerSearch(
      dto({
        categories: [{ id: NOT_BOOKABLE, name: "Unavailable Category" }],
        offerings: [
          { id: "s1", name: "Bookable Service", category_id: BOOKABLE },
        ],
      }),
      new Set([BOOKABLE]),
    );
    // Bookable service outranks an unavailable category.
    expect(out.results.map(r => r.name)).toEqual(["Bookable Service", "Unavailable Category"]);
  });

  it("keeps unavailable results rather than dropping them", () => {
    // Hiding them makes search look broken ("I know you offer plumbing").
    const out = adaptCustomerSearch(
      dto({ categories: [{ id: NOT_BOOKABLE, name: "Plumbing" }] }),
      new Set([BOOKABLE]),
    );
    expect(out.results).toHaveLength(1);
  });
});
