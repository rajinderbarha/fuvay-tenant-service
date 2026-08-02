jest.mock("../sessionStorage");
jest.mock("../refreshCoordinator", () => ({ refresh: jest.fn() }));
jest.mock("../accessContextApi", () => ({ fetchMappedAccessContext: jest.fn() }));
jest.mock("../sessionEvents", () => ({ emitSessionEvent: jest.fn() }));
jest.mock("../authApi", () => ({ logoutCurrentSession: jest.fn(), logoutAllSessions: jest.fn() }));
jest.mock("../../notifications/pushRegistration", () => ({ registerPushDevice: jest.fn(async () => ({ ok: true, permission: "granted" })), revokePushDevice: jest.fn(async () => {}) }));

import * as sessionManager from "../sessionManager";
import * as tokenCoordinator from "../tokenCoordinator";
import { readSessionBundle, writeSessionBundle, clearSessionBundle } from "../sessionStorage";
import { refresh as coordinatedRefresh } from "../refreshCoordinator";
import { fetchMappedAccessContext } from "../accessContextApi";
import { emitSessionEvent } from "../sessionEvents";
import * as authApi from "../authApi";

const READY_CONTEXT = {
  authenticated: true, userId: "u1", canonicalRole: "technician" as const, audience: "serviceos:staff" as const,
  tenantId: "t1", tenantStatus: "active", technicianId: "tech1", technicianStatus: "active",
};

// A JWT-shaped (unsigned, that's fine for local decode-only parsing) token
// with a controllable `exp` claim, matching the real payload structure.
function tokenWithExp(expSecondsFromNow: number): string {
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expSecondsFromNow })).toString("base64url");
  return `header.${payload}.sig`;
}

beforeEach(() => {
  tokenCoordinator.__resetTokenCoordinatorForTests();
  jest.clearAllMocks();
});

describe("sessionManager.restoreSession", () => {
  it("resolves unauthenticated when nothing is stored", async () => {
    (readSessionBundle as jest.Mock).mockResolvedValue(null);
    const snapshot = await sessionManager.restoreSession();
    expect(snapshot.authenticated).toBe(false);
    expect(coordinatedRefresh).not.toHaveBeenCalled();
  });

  it("validates directly (no refresh) when the stored access token is still fresh", async () => {
    const freshToken = tokenWithExp(3600);
    (readSessionBundle as jest.Mock).mockResolvedValue({ schemaVersion: 1, accessToken: freshToken, refreshToken: "r1", sessionId: null });
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: READY_CONTEXT, meta: {} });

    const snapshot = await sessionManager.restoreSession();

    expect(coordinatedRefresh).not.toHaveBeenCalled();
    expect(snapshot.authenticated).toBe(true);
    expect(snapshot.accessContext).toEqual(READY_CONTEXT);
  });

  it("performs one coordinated refresh when the stored access token is expired, then validates", async () => {
    const expiredToken = tokenWithExp(-3600);
    (readSessionBundle as jest.Mock).mockResolvedValue({ schemaVersion: 1, accessToken: expiredToken, refreshToken: "r1", sessionId: null });
    (coordinatedRefresh as jest.Mock).mockResolvedValue({ ok: true, accessToken: "a2" });
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: READY_CONTEXT, meta: {} });

    const snapshot = await sessionManager.restoreSession();

    expect(coordinatedRefresh).toHaveBeenCalledTimes(1);
    expect(snapshot.authenticated).toBe(true);
  });

  it("resolves unauthenticated (never optimistically authenticated) when the coordinated refresh fails", async () => {
    const expiredToken = tokenWithExp(-3600);
    (readSessionBundle as jest.Mock).mockResolvedValue({ schemaVersion: 1, accessToken: expiredToken, refreshToken: "r1", sessionId: null });
    (coordinatedRefresh as jest.Mock).mockResolvedValue({ ok: false });

    const snapshot = await sessionManager.restoreSession();

    expect(snapshot.authenticated).toBe(false);
    expect(fetchMappedAccessContext).not.toHaveBeenCalled();
  });
});

describe("sessionManager.validateSession", () => {
  it("clears the session on an auth-category failure from the access-context call", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: null });
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: false, error: { code: "SESSION_REVOKED", category: "auth", safeMessage: "x", retryable: false } });

    const snapshot = await sessionManager.validateSession();

    expect(snapshot.authenticated).toBe(false);
    expect(clearSessionBundle).toHaveBeenCalled();
  });

  it("emits TENANT_RESTRICTED when tenant status is not active", async () => {
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: { ...READY_CONTEXT, tenantStatus: "suspended" }, meta: {} });
    await sessionManager.validateSession();
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "TENANT_RESTRICTED" }));
  });

  it("emits TECHNICIAN_RESTRICTED when technician status is not active", async () => {
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: { ...READY_CONTEXT, technicianStatus: "suspended" }, meta: {} });
    await sessionManager.validateSession();
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "TECHNICIAN_RESTRICTED" }));
  });

  it("does not emit restriction events for a fully active technician/tenant", async () => {
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: READY_CONTEXT, meta: {} });
    await sessionManager.validateSession();
    expect(emitSessionEvent).not.toHaveBeenCalledWith(expect.objectContaining({ type: "TENANT_RESTRICTED" }));
    expect(emitSessionEvent).not.toHaveBeenCalledWith(expect.objectContaining({ type: "TECHNICIAN_RESTRICTED" }));
  });
});

describe("sessionManager.establishSession", () => {
  it("throws when the auth result has no refresh_token (force-password-change path)", async () => {
    await expect(sessionManager.establishSession({ access_token: "a1", refresh_token: null })).rejects.toThrow(/refresh_token/);
  });

  it("persists tokens, validates, and emits SESSION_ESTABLISHED", async () => {
    (fetchMappedAccessContext as jest.Mock).mockResolvedValue({ ok: true, data: READY_CONTEXT, meta: {} });
    const snapshot = await sessionManager.establishSession({ access_token: "a1", refresh_token: "r1" });
    expect(writeSessionBundle).toHaveBeenCalled();
    expect(snapshot.authenticated).toBe(true);
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "SESSION_ESTABLISHED" }));
  });
});

describe("sessionManager logout/revocation (spec section 19)", () => {
  it("revokeCurrentSession clears local session even when the backend call throws (offline logout)", async () => {
    (authApi.logoutCurrentSession as jest.Mock).mockRejectedValue(new Error("offline"));
    await sessionManager.revokeCurrentSession();
    expect(clearSessionBundle).toHaveBeenCalled();
  });

  it("revokeAllSessions reports remoteConfirmed:true with the count on success", async () => {
    (authApi.logoutAllSessions as jest.Mock).mockResolvedValue({ ok: true, data: { sessions_revoked: 3, message: "ok" }, meta: {} });
    const result = await sessionManager.revokeAllSessions();
    expect(result).toEqual({ remoteConfirmed: true, sessionsRevoked: 3 });
  });

  it("revokeAllSessions still clears locally and reports remoteConfirmed:false if the network call throws", async () => {
    (authApi.logoutAllSessions as jest.Mock).mockRejectedValue(new Error("offline"));
    const result = await sessionManager.revokeAllSessions();
    expect(result.remoteConfirmed).toBe(false);
    expect(clearSessionBundle).toHaveBeenCalled();
  });
});

describe("sessionManager.consumePendingDestination", () => {
  it("returns and clears the pending destination exactly once", () => {
    sessionManager.setPendingDestination("technician_app");
    expect(sessionManager.consumePendingDestination()).toBe("technician_app");
    expect(sessionManager.consumePendingDestination()).toBeNull();
  });
});

describe("sessionManager.markSessionTrusted", () => {
  it("is intentionally unsupported (backend has no post-hoc trust endpoint)", () => {
    expect(() => sessionManager.markSessionTrusted()).toThrow(/not supported/);
  });
});
