import * as authApi from "../../auth/authApi";
import * as sm from "../sessionManager";
import { clearSession, loadSession, saveSession } from "../tokenVault";
import { __resetSessionEventsForTests, getSessionSnapshot } from "../sessionEvents";
import { __resetRefreshCoordinatorForTests } from "../refreshCoordinator";
import { asCustomerId } from "../../../domain/ids";

const SecureStore = require("expo-secure-store");

const validAccessContext = {
  data: {
    user_id: "customer-1", canonical_role: "customer", audience: "serviceos:customer",
    tenant_id: null, tenant_status: null, technician_id: null, technician_status: null,
    enabled_verticals: [], capabilities: [],
  },
  requestId: "r1",
};

const staffAccessContext = {
  data: {
    user_id: "staff-1", canonical_role: "staff", audience: "serviceos:staff",
    tenant_id: "t1", tenant_status: "active", technician_id: null, technician_status: null,
    enabled_verticals: ["home_services"], capabilities: [],
  },
  requestId: "r1",
};

describe("sessionManager", () => {
  beforeEach(async () => {
    SecureStore.__resetMockStore();
    __resetSessionEventsForTests();
    __resetRefreshCoordinatorForTests();
    sm.__resetSessionManagerForTests();
    await clearSession();
    jest.restoreAllMocks();
    // Drive the state machine through its real uninitialized -> restoring
    // -> unauthenticated path (vault is empty at this point) rather than
    // hand-setting a state, so every test starts from a state the
    // machine itself considers legitimate.
    await sm.restoreSession();
  });

  it("password login success reaches the authenticated state with a valid customer session", async () => {
    jest.spyOn(authApi, "loginWithPassword").mockResolvedValue({
      data: { mfa_required: false, access_token: "acc-1", refresh_token: "ref-1", user: { id: "customer-1", role: "customer" } },
      requestId: "r1",
    });
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);

    const result = await sm.loginWithPassword({ email: "a@example.com", password: "pw" });
    expect(getSessionSnapshot().state).toBe("authenticated");
    expect((result as { customerId: string }).customerId).toBe("customer-1");
    expect((await loadSession())?.accessToken).toBe("acc-1");
  });

  it("password login returning mfa_required reaches mfa_required, never authenticated", async () => {
    jest.spyOn(authApi, "loginWithPassword").mockResolvedValue({
      data: { mfa_required: true, mfa_challenge_token: "chal-1" }, requestId: "r1",
    });

    const result = await sm.loginWithPassword({ email: "a@example.com", password: "pw" });
    expect(getSessionSnapshot().state).toBe("mfa_required");
    expect((result as { status: string }).status).toBe("challenge_required");
  });

  it("OTP verify success reaches authenticated", async () => {
    jest.spyOn(authApi, "verifyLoginOtp").mockResolvedValue({
      data: { mfa_required: false, access_token: "acc-2", refresh_token: "ref-2", user: { id: "customer-1", role: "customer" } },
      requestId: "r1",
    });
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);

    await sm.verifyLoginOtp("+919900000000", "123456");
    expect(getSessionSnapshot().state).toBe("authenticated");
  });

  it("completing an MFA challenge without a prior challenge throws and never authenticates", async () => {
    await expect(sm.completeMfaChallenge("123456")).rejects.toMatchObject({ category: "VALIDATION_FAILURE" });
    expect(getSessionSnapshot().state).not.toBe("authenticated");
  });

  it("completing a real MFA challenge transitions mfa_required -> authenticating -> authenticated", async () => {
    jest.spyOn(authApi, "loginWithPassword").mockResolvedValue({
      data: { mfa_required: true, mfa_challenge_token: "chal-2" }, requestId: "r1",
    });
    await sm.loginWithPassword({ email: "a@example.com", password: "pw" });
    expect(getSessionSnapshot().state).toBe("mfa_required");

    jest.spyOn(authApi, "completeMfaChallenge").mockResolvedValue({
      data: { mfa_required: false, access_token: "acc-3", refresh_token: "ref-3", user: { id: "customer-1", role: "customer" } },
      requestId: "r1",
    });
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);

    await sm.completeMfaChallenge("123456");
    expect(getSessionSnapshot().state).toBe("authenticated");
  });

  it("a staff/technician token completing login reaches invalid_audience, never authenticated", async () => {
    jest.spyOn(authApi, "loginWithPassword").mockResolvedValue({
      data: { mfa_required: false, access_token: "acc-staff", refresh_token: "ref-staff", user: { id: "staff-1", role: "staff" } },
      requestId: "r1",
    });
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(staffAccessContext);

    await sm.loginWithPassword({ email: "staff@example.com", password: "pw" });
    expect(getSessionSnapshot().state).toBe("invalid_audience");
    expect(await loadSession()).toBeNull();
  });

  it("logout clears the vault and lands on unauthenticated even when backend logout fails", async () => {
    jest.spyOn(authApi, "loginWithPassword").mockResolvedValue({
      data: { mfa_required: false, access_token: "acc-4", refresh_token: "ref-4", user: { id: "customer-1", role: "customer" } },
      requestId: "r1",
    });
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);
    await sm.loginWithPassword({ email: "a@example.com", password: "pw" });
    expect(getSessionSnapshot().state).toBe("authenticated");

    jest.spyOn(authApi, "logout").mockRejectedValue(new Error("network down"));
    await sm.logout();

    expect(getSessionSnapshot().state).toBe("unauthenticated");
    expect(await loadSession()).toBeNull();
  });

  it("restoreSession with no stored session reaches unauthenticated", async () => {
    __resetSessionEventsForTests();
    await sm.restoreSession();
    expect(getSessionSnapshot().state).toBe("unauthenticated");
  });

  it("restoreSession with a valid stored session reaches authenticated without a fresh login", async () => {
    await saveSession("stored-access", "stored-refresh", asCustomerId("customer-1"));
    jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);

    // beforeEach already ran restoreSession() once against an empty vault
    // (landing on unauthenticated) -- reset to uninitialized to simulate
    // a fresh cold start now that a session has been saved.
    __resetSessionEventsForTests();
    await sm.restoreSession();
    expect(getSessionSnapshot().state).toBe("authenticated");
  });

  it("restoreSession is idempotent -- a second concurrent call does not re-run restoration", async () => {
    await saveSession("stored-access", "stored-refresh", asCustomerId("customer-1"));
    __resetSessionEventsForTests();
    const getAccessContextSpy = jest.spyOn(authApi, "getAccessContext").mockResolvedValue(validAccessContext);

    await Promise.all([sm.restoreSession(), sm.restoreSession()]);
    expect(getAccessContextSpy).toHaveBeenCalledTimes(1);
  });
});
