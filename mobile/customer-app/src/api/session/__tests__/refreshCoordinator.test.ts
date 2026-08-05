import { getRefreshedAccessToken, bumpSessionEpoch, __resetRefreshCoordinatorForTests } from "../refreshCoordinator";
import { saveSession, clearSession, loadSession } from "../tokenVault";
import { asCustomerId } from "../../../domain/ids";
import * as authApi from "../../auth/authApi";

const SecureStore = require("expo-secure-store");
const customerId = asCustomerId("customer-1");

describe("refreshCoordinator", () => {
  beforeEach(async () => {
    SecureStore.__resetMockStore();
    __resetRefreshCoordinatorForTests();
    await clearSession();
    await saveSession("expired-access", "refresh-token-1", customerId);
  });

  afterEach(() => jest.restoreAllMocks());

  it("rotates tokens atomically on a successful refresh", async () => {
    jest.spyOn(authApi, "refreshSession").mockResolvedValue({
      data: { access_token: "new-access", refresh_token: "new-refresh" }, requestId: "r1",
    });
    const token = await getRefreshedAccessToken(customerId);
    expect(token).toBe("new-access");
    const stored = await loadSession();
    expect(stored?.refreshToken).toBe("new-refresh");
  });

  it("coordinates multiple concurrent callers into exactly one HTTP refresh call", async () => {
    let resolveFn: (v: { data: { access_token: string; refresh_token: string }; requestId: string }) => void = () => {};
    const spy = jest.spyOn(authApi, "refreshSession").mockReturnValue(
      new Promise(resolve => { resolveFn = resolve; }) as ReturnType<typeof authApi.refreshSession>,
    );

    const p1 = getRefreshedAccessToken(customerId);
    const p2 = getRefreshedAccessToken(customerId);
    const p3 = getRefreshedAccessToken(customerId);

    resolveFn({ data: { access_token: "shared-access", refresh_token: "shared-refresh" }, requestId: "r1" });

    const [t1, t2, t3] = await Promise.all([p1, p2, p3]);
    expect(t1).toBe("shared-access");
    expect(t2).toBe("shared-access");
    expect(t3).toBe("shared-access");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("rejects and clears the session when the backend reports refresh reuse (family revoked)", async () => {
    const { DomainError } = require("../../../domain/errors");
    jest.spyOn(authApi, "refreshSession").mockRejectedValue(
      new DomainError({ category: "SESSION_EXPIRED", diagnostic: "Security alert: token reuse detected." }),
    );
    await expect(getRefreshedAccessToken(customerId)).rejects.toMatchObject({ category: "SESSION_EXPIRED" });
    expect(await loadSession()).toBeNull();
  });

  it("discards a refresh response that resolves after the session epoch has moved (logout mid-flight)", async () => {
    let resolveFn: (v: { data: { access_token: string; refresh_token: string }; requestId: string }) => void = () => {};
    jest.spyOn(authApi, "refreshSession").mockReturnValue(
      new Promise(resolve => { resolveFn = resolve; }) as ReturnType<typeof authApi.refreshSession>,
    );
    const pending = getRefreshedAccessToken(customerId);
    bumpSessionEpoch(); // simulate logout happening mid-refresh
    resolveFn({ data: { access_token: "late-access", refresh_token: "late-refresh" }, requestId: "r1" });
    await expect(pending).rejects.toMatchObject({ category: "SESSION_EXPIRED" });
  });

  it("does not clear the session on a plain network failure during refresh", async () => {
    const { DomainError } = require("../../../domain/errors");
    jest.spyOn(authApi, "refreshSession").mockRejectedValue(
      new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "offline" }),
    );
    await expect(getRefreshedAccessToken(customerId)).rejects.toMatchObject({ category: "NETWORK_UNAVAILABLE" });
    expect(await loadSession()).not.toBeNull();
  });
});
