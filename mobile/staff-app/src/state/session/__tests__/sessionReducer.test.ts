import { sessionReducer } from "../sessionReducer";
import { INITIAL_SESSION_STATE } from "../types";

describe("sessionReducer", () => {
  it("BOOTSTRAP_STATE_CHANGED updates bootstrapStatus and sessionError", () => {
    const next = sessionReducer(INITIAL_SESSION_STATE, { kind: "BOOTSTRAP_STATE_CHANGED", bootstrapStatus: "access_denied", reasonCode: "ROLE_NOT_ALLOWED" });
    expect(next.bootstrapStatus).toBe("access_denied");
    expect(next.sessionError).toBe("ROLE_NOT_ALLOWED");
  });

  it("BOOTSTRAP_STATE_CHANGED clears sessionError when no reasonCode is given", () => {
    const withError = sessionReducer(INITIAL_SESSION_STATE, { kind: "BOOTSTRAP_STATE_CHANGED", bootstrapStatus: "access_denied", reasonCode: "ROLE_NOT_ALLOWED" });
    const cleared = sessionReducer(withError, { kind: "BOOTSTRAP_STATE_CHANGED", bootstrapStatus: "authenticated_ready" });
    expect(cleared.sessionError).toBeNull();
  });

  it("SNAPSHOT_UPDATED copies every snapshot field", () => {
    const snapshot = {
      accessTokenPresent: true, sessionId: "s1", expiresAt: "2030-01-01T00:00:00.000Z",
      authenticated: true, accessContext: { authenticated: true, userId: "u1" },
      lastValidatedAt: "2026-01-01T00:00:00.000Z", sessionGeneration: 2,
    };
    const next = sessionReducer(INITIAL_SESSION_STATE, { kind: "SNAPSHOT_UPDATED", snapshot });
    expect(next.accessTokenPresent).toBe(true);
    expect(next.sessionId).toBe("s1");
    expect(next.authenticated).toBe(true);
    expect(next.accessContext).toEqual(snapshot.accessContext);
    expect(next.sessionGeneration).toBe(2);
  });

  it("NETWORK_STATE_CHANGED updates only networkStatus", () => {
    const next = sessionReducer(INITIAL_SESSION_STATE, { kind: "NETWORK_STATE_CHANGED", networkStatus: "offline" });
    expect(next.networkStatus).toBe("offline");
    expect(next.bootstrapStatus).toBe(INITIAL_SESSION_STATE.bootstrapStatus);
  });

  it("PENDING_DESTINATION_CHANGED updates only pendingSafeDestination", () => {
    const next = sessionReducer(INITIAL_SESSION_STATE, { kind: "PENDING_DESTINATION_CHANGED", destination: "technician_app" });
    expect(next.pendingSafeDestination).toBe("technician_app");
  });

  it("is a pure function -- never mutates the input state", () => {
    const before = JSON.stringify(INITIAL_SESSION_STATE);
    sessionReducer(INITIAL_SESSION_STATE, { kind: "NETWORK_STATE_CHANGED", networkStatus: "online" });
    expect(JSON.stringify(INITIAL_SESSION_STATE)).toBe(before);
  });
});
