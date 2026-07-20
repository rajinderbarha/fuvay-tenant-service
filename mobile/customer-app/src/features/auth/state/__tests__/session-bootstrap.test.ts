import { bootstrapSession } from "../session-bootstrap";
import { persistSession, __resetSessionStoreForTests } from "../session-store";
import { secureStorage } from "../../../../storage/secure-storage";
import { SECURE_STORAGE_KEYS } from "../../../../storage/storage-keys";
import { ApiError } from "../../../../api/api-errors";
import type { CustomerSession } from "../../domain/session";

jest.mock("../../api/auth-api", () => ({ authApi: { me: jest.fn(), refreshToken: jest.fn() } }));
// eslint-disable-next-line @typescript-eslint/no-var-requires
const mockedAuthApi = require("../../api/auth-api").authApi;

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

describe("bootstrapSession", () => {
  beforeEach(async () => {
    __resetSessionStoreForTests();
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.accessToken);
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.refreshToken);
    jest.clearAllMocks();
  });

  it("returns guest with no persisted tokens, without calling the API", async () => {
    const status = await bootstrapSession();
    expect(status).toBe("guest");
    expect(mockedAuthApi.me).not.toHaveBeenCalled();
  });

  it("returns authenticated and refreshes the profile when tokens are valid", async () => {
    await persistSession(session());
    mockedAuthApi.me.mockResolvedValue({
      user_id: "u1",
      id: "u1",
      email: "jane@example.com",
      phone: "+919876543210",
      full_name: "Jane Doe",
      display_name: null,
      language: "en",
      timezone: "UTC",
      role: "customer",
      tenant_id: null,
      is_verified: true,
      is_mfa_enabled: false,
      is_active: true,
      onboarding_complete: true,
      force_password_change: false,
      password_reset_required: false,
      temporary_password_active: false,
      password_changed_at: null,
      avatar_url: null,
      profile_photo_media_id: null,
      last_login_at: null,
      created_at: "2026-01-01T00:00:00.000Z",
      permissions: [],
    });
    const status = await bootstrapSession();
    expect(status).toBe("authenticated");
  });

  it("keeps a transient network failure from destroying an otherwise-valid local session state", async () => {
    await persistSession(session());
    mockedAuthApi.me.mockRejectedValue(new ApiError({ category: "network_error", message: "offline" }));
    const status = await bootstrapSession();
    // Already "authenticated" in memory from persistSession() above — a
    // transient network failure on this run reports the last-known status
    // rather than forcing guest. 401 handling itself is no longer
    // bootstrapSession's responsibility — see auth-refresh-coordinator.test.ts.
    expect(status).toBe("authenticated");
  });
});
