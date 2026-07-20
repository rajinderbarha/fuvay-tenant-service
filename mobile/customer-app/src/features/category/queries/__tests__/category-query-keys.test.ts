import { categoryQueryKeys } from "../category-queries";

describe("categoryQueryKeys", () => {
  it("detail key includes locale and tenant", () => {
    expect(categoryQueryKeys.detail("cat-1", "hi", "tenant-1")).toEqual(["category", "detail", "cat-1", "hi", "tenant-1"]);
  });

  it("detail key uses a stable placeholder for an absent tenant", () => {
    expect(categoryQueryKeys.detail("cat-1", "en", undefined)).toEqual(["category", "detail", "cat-1", "en", "no-tenant"]);
  });

  it("offerings key is distinct per category", () => {
    const a = categoryQueryKeys.offerings("cat-1", "en", undefined);
    const b = categoryQueryKeys.offerings("cat-2", "en", undefined);
    expect(a).not.toEqual(b);
  });

  it("offerings key is distinct per locale", () => {
    const a = categoryQueryKeys.offerings("cat-1", "en", undefined);
    const b = categoryQueryKeys.offerings("cat-1", "pa", undefined);
    expect(a).not.toEqual(b);
  });

  it("offerings key is distinct per tenant", () => {
    const a = categoryQueryKeys.offerings("cat-1", "en", "tenant-a");
    const b = categoryQueryKeys.offerings("cat-1", "en", "tenant-b");
    expect(a).not.toEqual(b);
  });
});
