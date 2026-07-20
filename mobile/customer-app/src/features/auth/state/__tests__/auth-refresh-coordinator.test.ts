import { bindRefreshCoordinator, __resetRefreshCoordinatorForTests } from "../auth-refresh-coordinator";
import { persistSession, getSessionState, __resetSessionStoreForTests } from "../session-store";
import { handleUnauthorized, setUnauthorizedHandler } from "../../../../api/request-context";
import { secureStorage } from "../../../../storage/secure-storage";
import { SECURE_STORAGE_KEYS } from "../../../../storage/storage-keys";
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

const validProfile = {
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
};

describe("auth-refresh-coordinator", () => {
  beforeEach(async () => {
    __resetSessionStoreForTests();
    __resetRefreshCoordinatorForTests();
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.accessToken);
    await secureStorage.removeItem(SECURE_STORAGE_KEYS.refreshToken);
    jest.clearAllMocks();
  });

  afterEach(() => {
    setUnauthorizedHandler(null);
  });

  it("registers as the api-client unauthorized handler", async () => {
    bindRefreshCoordinator();
    // With no session, the handler resolves false without ever calling the network.
    const result = await handleUnauthorized();
    expect(result).toBe(false);
    expect(mockedAuthApi.refreshToken).not.toHaveBeenCalled();
  });

  it("refreshes and persists a new session on success", async () => {
    await persistSession(session());
    mockedAuthApi.refreshToken.mockResolvedValue({ access_token: "at2", refresh_token: "rt2" });
    mockedAuthApi.me.mockResolvedValue(validProfile);
    bindRefreshCoordinator();

    const result = await handleUnauthorized();
    expect(result).toBe(true);
    expect(getSessionState().session?.accessToken).toBe("at2");
  });

  it("clears the session and returns false when refresh fails", async () => {
    await persistSession(session());
    mockedAuthApi.refreshToken.mockRejectedValue(new Error("expired"));
    bindRefreshCoordinator();

    const result = await handleUnauthorized();
    expect(result).toBe(false);
    expect(getSessionState().status).toBe("guest");
  });

  it("shares one in-flight refresh across concurrent callers (single-flight)", async () => {
    await persistSession(session());
    let resolveRefresh!: (value: { access_token: string; refresh_token: string }) => void;
    mockedAuthApi.refreshToken.mockReturnValue(new Promise((resolve) => (resolveRefresh = resolve)));
    mockedAuthApi.me.mockResolvedValue(validProfile);
    bindRefreshCoordinator();

    const first = handleUnauthorized();
    const second = handleUnauthorized();
    resolveRefresh({ access_token: "at2", refresh_token: "rt2" });

    const [firstResult, secondResult] = await Promise.all([first, second]);
    expect(firstResult).toBe(true);
    expect(secondResult).toBe(true);
    expect(mockedAuthApi.refreshToken).toHaveBeenCalledTimes(1);
  });
});
