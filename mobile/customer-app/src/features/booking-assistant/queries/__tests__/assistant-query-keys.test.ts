import { assistantQueryKeys } from "../assistant-queries";

describe("assistantQueryKeys", () => {
  it("issueTypes key is scoped by category, locale and tenant", () => {
    expect(assistantQueryKeys.issueTypes("cat-1", "en", "tenant-1")).toEqual(["assistant", "issue-types", "cat-1", "en", "tenant-1"]);
  });

  it("uses a stable placeholder for an absent tenant", () => {
    expect(assistantQueryKeys.issueTypes("cat-1", "en", undefined)).toEqual(["assistant", "issue-types", "cat-1", "en", "no-tenant"]);
  });

  it("produces distinct keys per category for every catalog", () => {
    expect(assistantQueryKeys.issueTypes("cat-1", "en", undefined)).not.toEqual(assistantQueryKeys.issueTypes("cat-2", "en", undefined));
    expect(assistantQueryKeys.serviceOptions("cat-1", "en", undefined)).not.toEqual(assistantQueryKeys.serviceOptions("cat-2", "en", undefined));
    expect(assistantQueryKeys.brands("cat-1", "en", undefined)).not.toEqual(assistantQueryKeys.brands("cat-2", "en", undefined));
    expect(assistantQueryKeys.serviceTypes("cat-1", "en", undefined)).not.toEqual(assistantQueryKeys.serviceTypes("cat-2", "en", undefined));
  });

  it("distinguishes the four catalog kinds from each other under the same category", () => {
    const keys = [
      assistantQueryKeys.issueTypes("cat-1", "en", undefined),
      assistantQueryKeys.serviceOptions("cat-1", "en", undefined),
      assistantQueryKeys.brands("cat-1", "en", undefined),
      assistantQueryKeys.serviceTypes("cat-1", "en", undefined),
    ];
    const unique = new Set(keys.map((k) => JSON.stringify(k)));
    expect(unique.size).toBe(4);
  });

  it("produces distinct keys per locale (Punjabi never mixes with English cache)", () => {
    expect(assistantQueryKeys.issueTypes("cat-1", "en", undefined)).not.toEqual(assistantQueryKeys.issueTypes("cat-1", "pa", undefined));
  });
});
