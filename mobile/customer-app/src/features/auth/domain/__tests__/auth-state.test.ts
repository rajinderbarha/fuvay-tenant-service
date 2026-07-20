import { deriveAuthState } from "../auth-state";

function inputs(overrides: Partial<Parameters<typeof deriveAuthState>[0]> = {}) {
  return {
    sessionStatus: "unknown" as const,
    restoring: false,
    refreshing: false,
    loggingOut: false,
    ...overrides,
  };
}

describe("deriveAuthState", () => {
  it("is restoring before session restoration completes, regardless of session status", () => {
    expect(deriveAuthState(inputs({ restoring: true, sessionStatus: "authenticated" }))).toBe("restoring");
  });

  it("is guest when the session store resolves guest", () => {
    expect(deriveAuthState(inputs({ sessionStatus: "guest" }))).toBe("guest");
  });

  it("is authenticated when the session store resolves authenticated", () => {
    expect(deriveAuthState(inputs({ sessionStatus: "authenticated" }))).toBe("authenticated");
  });

  it("reflects each OTP flow step", () => {
    expect(deriveAuthState(inputs({ otpFlowStep: "sending" }))).toBe("otp-requesting");
    expect(deriveAuthState(inputs({ otpFlowStep: "enter-otp" }))).toBe("otp-requested");
    expect(deriveAuthState(inputs({ otpFlowStep: "verifying" }))).toBe("otp-verifying");
  });

  it("is refreshing when a token refresh is in flight, overriding authenticated", () => {
    expect(deriveAuthState(inputs({ sessionStatus: "authenticated", refreshing: true }))).toBe("refreshing");
  });

  it("is logging-out when a logout is in flight, overriding authenticated", () => {
    expect(deriveAuthState(inputs({ sessionStatus: "authenticated", loggingOut: true }))).toBe("logging-out");
  });

  it("is error when a last error category is present and nothing more urgent is happening", () => {
    expect(deriveAuthState(inputs({ lastErrorCategory: "OTP_INVALID" }))).toBe("error");
  });

  it("defaults to unknown when nothing else applies", () => {
    expect(deriveAuthState(inputs())).toBe("unknown");
  });

  it("restoring always wins over every other flag (highest priority)", () => {
    expect(deriveAuthState(inputs({ restoring: true, refreshing: true, loggingOut: true, otpFlowStep: "verifying" }))).toBe("restoring");
  });
});
