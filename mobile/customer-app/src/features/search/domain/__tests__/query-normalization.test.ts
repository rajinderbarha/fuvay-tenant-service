import { normalizeSearchQuery, isSearchableQuery, MIN_QUERY_LENGTH, queryLengthBucket, resultCountBucket } from "../query-normalization";

describe("normalizeSearchQuery", () => {
  it("trims leading and trailing whitespace", () => {
    expect(normalizeSearchQuery("  ac repair  ")).toBe("ac repair");
  });

  it("collapses internal whitespace runs to a single space", () => {
    expect(normalizeSearchQuery("ac    repair")).toBe("ac repair");
  });

  it("strips control characters", () => {
    expect(normalizeSearchQuery("ac\x00repair\x1F")).toBe("acrepair");
  });

  it("preserves non-Latin Unicode scripts untouched (Hindi, Punjabi)", () => {
    expect(normalizeSearchQuery("एसी रिपेयर")).toBe("एसी रिपेयर");
    expect(normalizeSearchQuery("ਏਸੀ ਮੁਰੰਮਤ")).toBe("ਏਸੀ ਮੁਰੰਮਤ");
  });

  it("enforces a maximum length", () => {
    const long = "a".repeat(200);
    expect(normalizeSearchQuery(long).length).toBe(100);
  });
});

describe("isSearchableQuery", () => {
  it("rejects a query shorter than the minimum length", () => {
    expect(isSearchableQuery("a")).toBe(false);
  });

  it("accepts a query at exactly the minimum length", () => {
    expect(isSearchableQuery("a".repeat(MIN_QUERY_LENGTH))).toBe(true);
  });

  it("rejects an empty query", () => {
    expect(isSearchableQuery("")).toBe(false);
  });
});

describe("queryLengthBucket", () => {
  it("buckets short, medium and long queries without exposing the raw text", () => {
    expect(queryLengthBucket("ac")).toBe("short");
    expect(queryLengthBucket("ac repair service")).toBe("medium");
    expect(queryLengthBucket("a".repeat(30))).toBe("long");
  });
});

describe("resultCountBucket", () => {
  it("buckets zero, few and many results", () => {
    expect(resultCountBucket(0)).toBe("zero");
    expect(resultCountBucket(3)).toBe("few");
    expect(resultCountBucket(20)).toBe("many");
  });
});
