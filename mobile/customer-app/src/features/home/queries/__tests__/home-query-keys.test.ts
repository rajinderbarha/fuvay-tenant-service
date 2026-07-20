import { homeQueryKeys } from "../home-queries";

describe("homeQueryKeys.categories", () => {
  it("includes locale and tenant in the key", () => {
    expect(homeQueryKeys.categories("hi", "tenant-1")).toEqual(["home", "categories", "hi", "tenant-1"]);
  });

  it("produces a distinct key for a different locale", () => {
    const a = homeQueryKeys.categories("en", undefined);
    const b = homeQueryKeys.categories("hi", undefined);
    expect(a).not.toEqual(b);
  });

  it("produces a distinct key for a different tenant", () => {
    const a = homeQueryKeys.categories("en", "tenant-a");
    const b = homeQueryKeys.categories("en", "tenant-b");
    expect(a).not.toEqual(b);
  });

  it("uses a stable placeholder for an absent tenant rather than undefined in the key", () => {
    expect(homeQueryKeys.categories("en", undefined)).toEqual(["home", "categories", "en", "no-tenant"]);
  });
});
