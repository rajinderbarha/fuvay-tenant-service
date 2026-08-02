jest.mock("../../../services/auth/sessionManager", () => ({ restoreSession: jest.fn() }));
jest.mock("../../../services/api/networkState", () => ({ isOffline: jest.fn() }));

import { runSessionBootstrap } from "../sessionBootstrap";
import * as sessionManager from "../../../services/auth/sessionManager";
import { isOffline } from "../../../services/api/networkState";

beforeEach(() => jest.clearAllMocks());

const READY_SNAPSHOT = {
  accessTokenPresent: true, sessionId: null, expiresAt: null, authenticated: true,
  accessContext: {
    authenticated: true, canonicalRole: "technician" as const, audience: "serviceos:staff" as const,
    tenantId: "t1", tenantStatus: "active", technicianId: "tech1", technicianStatus: "active",
  },
  lastValidatedAt: null, sessionGeneration: 1,
};

describe("runSessionBootstrap", () => {
  it("resolves service_unavailable (locked/offline state) when the device is offline at cold start, without calling restoreSession", async () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    const result = await runSessionBootstrap();
    expect(result.bootstrapStatus).toBe("service_unavailable");
    expect(sessionManager.restoreSession).not.toHaveBeenCalled();
  });

  it("resolves service_unavailable on a bounded startup timeout, never authenticated", async () => {
    (isOffline as jest.Mock).mockReturnValue(false);
    (sessionManager.restoreSession as jest.Mock).mockReturnValue(new Promise(() => {})); // never resolves
    const result = await runSessionBootstrap();
    expect(result.bootstrapStatus).toBe("service_unavailable");
    expect(result.snapshot.authenticated).toBe(false);
  }, 15000);

  it("resolves authenticated_ready for a fully valid restored session", async () => {
    (isOffline as jest.Mock).mockReturnValue(false);
    (sessionManager.restoreSession as jest.Mock).mockResolvedValue(READY_SNAPSHOT);
    const result = await runSessionBootstrap();
    expect(result.bootstrapStatus).toBe("authenticated_ready");
  });

  it("resolves unauthenticated when nothing was restored", async () => {
    (isOffline as jest.Mock).mockReturnValue(false);
    (sessionManager.restoreSession as jest.Mock).mockResolvedValue({
      accessTokenPresent: false, sessionId: null, expiresAt: null, authenticated: false,
      accessContext: { authenticated: false }, lastValidatedAt: null, sessionGeneration: 0,
    });
    const result = await runSessionBootstrap();
    expect(result.bootstrapStatus).toBe("unauthenticated");
  });

  it("resolves tenant_suspended when the restored context has a suspended tenant", async () => {
    (isOffline as jest.Mock).mockReturnValue(false);
    (sessionManager.restoreSession as jest.Mock).mockResolvedValue({
      ...READY_SNAPSHOT, accessContext: { ...READY_SNAPSHOT.accessContext, tenantStatus: "suspended" },
    });
    const result = await runSessionBootstrap();
    expect(result.bootstrapStatus).toBe("tenant_suspended");
  });
});
