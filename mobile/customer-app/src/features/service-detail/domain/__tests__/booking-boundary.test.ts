import { evaluateBookingBoundary } from "../booking-boundary";

describe("evaluateBookingBoundary", () => {
  it("requires authentication", () => {
    expect(evaluateBookingBoundary({ authenticated: false })).toBe("AUTH_REQUIRED");
  });

  it("is available when authenticated (CUSTOMER-L5-05 real assistant, no longer dev-gated)", () => {
    expect(evaluateBookingBoundary({ authenticated: true })).toBe("AVAILABLE");
  });
});
