import { searchQueryKeys } from "../search-queries";

describe("searchQueryKeys.results", () => {
  it("is scoped by normalized query, category, locale and tenant", () => {
    expect(searchQueryKeys.results("ac repair", "cat-1", "en", "tenant-1")).toEqual(["search", "results", "ac repair", "cat-1", "en", "tenant-1"]);
  });

  it("uses a stable placeholder when no category scope is set", () => {
    expect(searchQueryKeys.results("ac repair", undefined, "en", undefined)).toEqual(["search", "results", "ac repair", "all-categories", "en", "no-tenant"]);
  });

  it("produces distinct keys for different normalized queries", () => {
    const a = searchQueryKeys.results("ac repair", undefined, "en", undefined);
    const b = searchQueryKeys.results("plumbing", undefined, "en", undefined);
    expect(a).not.toEqual(b);
  });

  it("produces distinct keys for different locales (Punjabi cache never mixes with English)", () => {
    const a = searchQueryKeys.results("ac", undefined, "en", undefined);
    const b = searchQueryKeys.results("ac", undefined, "pa", undefined);
    expect(a).not.toEqual(b);
  });
});
