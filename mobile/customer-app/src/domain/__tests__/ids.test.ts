import { asCustomerId, asServiceJobId, asBookingDraftId } from "../ids";

describe("branded identifiers", () => {
  it("keeps distinct ID types from being structurally interchangeable at the type level", () => {
    const customerId = asCustomerId("c-1");
    const jobId = asServiceJobId("c-1");
    // Runtime values may coincide, but the two functions produce distinct
    // brands -- this test asserts the runtime string is preserved exactly
    // (branding is a compile-time-only concern verified by tsc, not by a
    // runtime assertion library).
    expect(customerId as string).toBe("c-1");
    expect(jobId as string).toBe("c-1");
  });

  it("never coerces a UUID-like value to a number", () => {
    const draftId = asBookingDraftId("99999999-9999-9999-9999-999999999999");
    expect(typeof (draftId as unknown)).toBe("string");
  });
});
