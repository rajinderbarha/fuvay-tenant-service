import { addressQueryKeys } from "../address-queries";

describe("addressQueryKeys.list", () => {
  it("is scoped by locale and tenant", () => {
    expect(addressQueryKeys.list("en", "tenant-1")).toEqual(["address", "list", "en", "tenant-1"]);
  });

  it("uses a stable placeholder for an absent tenant", () => {
    expect(addressQueryKeys.list("en", undefined)).toEqual(["address", "list", "en", "no-tenant"]);
  });

  it("produces distinct keys for different locales (Punjabi cache never mixes with English)", () => {
    expect(addressQueryKeys.list("en", undefined)).not.toEqual(addressQueryKeys.list("pa", undefined));
  });
});
