import { isValidTransition, assertValidTransition, InvalidSessionTransitionError } from "../sessionStateMachine";

describe("session state machine", () => {
  it("allows the canonical happy-path transitions", () => {
    expect(isValidTransition("uninitialized", "restoring")).toBe(true);
    expect(isValidTransition("unauthenticated", "authenticating")).toBe(true);
    expect(isValidTransition("authenticating", "authenticated")).toBe(true);
    expect(isValidTransition("authenticated", "refreshing")).toBe(true);
    expect(isValidTransition("refreshing", "authenticated")).toBe(true);
  });

  it("prohibits mfa_required -> authenticated directly (must re-enter authenticating)", () => {
    expect(isValidTransition("mfa_required", "authenticated")).toBe(false);
  });

  it("prohibits session_expired -> authenticated without a fresh login", () => {
    expect(isValidTransition("session_expired", "authenticated")).toBe(false);
    expect(isValidTransition("session_expired", "unauthenticated")).toBe(true);
  });

  it("prohibits invalid_audience -> authenticated (never enters customer tabs)", () => {
    expect(isValidTransition("invalid_audience", "authenticated")).toBe(false);
  });

  it("prohibits account_suspended -> authenticated", () => {
    expect(isValidTransition("account_suspended", "authenticated")).toBe(false);
  });

  it("throws for an invalid transition via assertValidTransition", () => {
    expect(() => assertValidTransition("session_expired", "authenticated")).toThrow(InvalidSessionTransitionError);
  });
});
