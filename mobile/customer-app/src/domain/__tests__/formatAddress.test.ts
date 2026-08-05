import { formatSavedAddress } from "../formatAddress";
import { CustomerSavedAddress } from "../customerSavedAddress";

function address(overrides: Partial<CustomerSavedAddress> = {}): CustomerSavedAddress {
  return {
    id: "a-1", label: "Home", recipientName: null, mobile: null,
    line1: "House 24, Model Town", line2: null, landmark: null,
    city: "Ludhiana", district: null, state: "Punjab", country: "India",
    postalCode: "141002", isDefault: true,
    createdAt: "2026-01-01T00:00:00Z" as CustomerSavedAddress["createdAt"], updatedAt: null,
    ...overrides,
  };
}

describe("formatSavedAddress", () => {
  it("formats line1 + city/state/postal into one readable string", () => {
    expect(formatSavedAddress(address())).toBe("House 24, Model Town, Ludhiana, Punjab 141002");
  });

  it("includes line2 and landmark when present, in order", () => {
    const result = formatSavedAddress(address({ line2: "Near Bus Stand", landmark: "Opposite Park" }));
    expect(result).toBe("House 24, Model Town, Near Bus Stand, Opposite Park, Ludhiana, Punjab 141002");
  });

  it("never includes an empty/whitespace-only line2", () => {
    const result = formatSavedAddress(address({ line2: "   " }));
    expect(result).not.toContain("  ,");
  });
});
