import { mapAuthStatus, mapAccountStatus } from "../useNavigationSnapshot";
import { resolveDestination } from "../guards/resolveDestination";
import { SessionSnapshot } from "../../api/session/sessionEvents";

function snapshot(overrides: Partial<SessionSnapshot> = {}): SessionSnapshot {
  return { state: "authenticated", context: null, epoch: 0, ...overrides };
}

describe("session -> navigation mapping (spec section 28)", () => {
  it("maps authenticated/refreshing to authenticated_customer", () => {
    expect(mapAuthStatus("authenticated")).toBe("authenticated_customer");
    expect(mapAuthStatus("refreshing")).toBe("authenticated_customer");
  });

  it("maps session_expired and invalid_audience to their own distinct statuses", () => {
    expect(mapAuthStatus("session_expired")).toBe("session_expired");
    expect(mapAuthStatus("invalid_audience")).toBe("invalid_audience");
  });

  it("maps mfa_required to unauthenticated (no dedicated MFA route exists until a later phase)", () => {
    expect(mapAuthStatus("mfa_required")).toBe("unauthenticated");
  });

  it("maps account_suspended state to a suspended account status", () => {
    expect(mapAccountStatus("account_suspended", snapshot({ state: "account_suspended" }))).toBe("suspended");
  });

  it("end-to-end: an authenticated session reaches the customer app stack via the real resolver", () => {
    const dest = resolveDestination({
      bootstrap: "ready",
      auth: mapAuthStatus("authenticated"),
      audience: "serviceos:customer",
      account: mapAccountStatus("authenticated", snapshot()),
      appVersion: "supported",
      platform: "available",
      storage: "available",
      network: "online",
      enabledVerticals: { enabled: ["home_services"] },
    });
    expect(dest.tree).toBe("CustomerAppStack");
  });

  it("end-to-end: a staff/invalid-audience session never reaches the customer app stack", () => {
    const dest = resolveDestination({
      bootstrap: "ready",
      auth: mapAuthStatus("invalid_audience"),
      audience: "serviceos:staff",
      account: "active",
      appVersion: "supported",
      platform: "available",
      storage: "available",
      network: "online",
      enabledVerticals: { enabled: ["home_services"] },
    });
    expect(dest.tree).toBe("ExceptionalStateStack");
    expect((dest as { screen: string }).screen).toBe("InvalidAccess");
  });

  it("end-to-end: session_expired never reaches the customer app stack, even with a stale-looking network state", () => {
    const dest = resolveDestination({
      bootstrap: "ready",
      auth: mapAuthStatus("session_expired"),
      audience: null,
      account: "active",
      appVersion: "supported",
      platform: "available",
      storage: "available",
      network: "online",
      enabledVerticals: { enabled: ["home_services"] },
    });
    expect((dest as { screen: string }).screen).toBe("SessionExpired");
  });
});
