import { hydrateSessionTokens, persistSession, clearSession, getSessionState, updateSessionProfile, __resetSessionStoreForTests } from "../session-store";
import { secureStorage } from "../../../../storage/secure-storage";
import { SECURE_STORAGE_KEYS } from "../../../../storage/storage-keys";
import type { CustomerSession } from "../../domain/session";

function session(overrides: Partial<CustomerSession> = {}): CustomerSession {
  return {
    accessToken: "at1",
    refreshToken: "rt1",
    userId: "u1",
    fullName: "Jane Doe",
    displayName: null,
    phone: "+919876543210",
    email: "jane@example.com",
    language: "en",
    role: "customer",
    tenantId: null,
    isVerified: true,
    onboardingComplete: true,
    avatarUrl: null,
    ...overrides,
  };
}

describe("session-store", () => {
  beforeEach(async () => {
    __resetSessionStoreForTests();
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.accessToken);
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.refreshToken);
  });

  it("hydrates as null with no persisted tokens and marks status guest", async () => {
    const tokens = await hydrateSessionTokens();
    expect(tokens).toBeNull();
    expect(getSessionState().status).toBe("guest");
  });

  it("persists a session and marks status authenticated", async () => {
    await persistSession(session());
    expect(getSessionState().status).toBe("authenticated");
    expect(getSessionState().session?.userId).toBe("u1");
  });

  it("hydrates persisted tokens after persistSession", async () => {
    await persistSession(session());
    const tokens = await hydrateSessionTokens();
    expect(tokens).toEqual({ accessToken: "at1", refreshToken: "rt1" });
  });

  it("clears the session and the underlying secure storage", async () => {
    await persistSession(session());
    await clearSession();
    expect(getSessionState().status).toBe("guest");
    expect(getSessionState().session).toBeNull();
    expect(await secureStorage.getItem(SECURE_STORAGE_KEYS.accessToken)).toBeNull();
  });

  it("updateSessionProfile merges a patch into the existing session", async () => {
    await persistSession(session());
    updateSessionProfile({ fullName: "Jane Q. Doe" });
    expect(getSessionState().session?.fullName).toBe("Jane Q. Doe");
    expect(getSessionState().session?.userId).toBe("u1");
  });

  it("updateSessionProfile is a no-op when there is no active session", () => {
    updateSessionProfile({ fullName: "Should not apply" });
    expect(getSessionState().session).toBeNull();
  });

  it("still marks the session authenticated in-memory even if the secure-storage write fails, but logs a warning", async () => {
    const setItemSpy = jest.spyOn(secureStorage, "setItem").mockResolvedValueOnce(false);
    await persistSession(session());
    expect(getSessionState().status).toBe("authenticated");
    setItemSpy.mockRestore();
  });
});
