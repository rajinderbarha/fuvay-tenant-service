import { resolveAddressCapabilities } from "../addressCapabilities";

describe("resolveAddressCapabilities", () => {
  it("reflects the confirmed real backend contract: all four actions are real as of the Add/Edit Address phase", () => {
    expect(resolveAddressCapabilities()).toEqual({
      canCreate: true,
      canEdit: true,
      canDelete: true,
      canSetDefault: true,
    });
  });
});
