import { resolveDestination, destinationSignature } from "../resolveDestination";
import { AppNavigationSnapshot } from "../types";

function baseSnapshot(overrides: Partial<AppNavigationSnapshot> = {}): AppNavigationSnapshot {
  return {
    bootstrap: "ready",
    auth: "authenticated_customer",
    audience: "serviceos:customer",
    account: "active",
    appVersion: "supported",
    platform: "available",
    storage: "available",
    network: "online",
    enabledVerticals: { enabled: ["home_services"] },
    pendingDeepLink: undefined,
    ...overrides,
  };
}

describe("resolveDestination — route resolution", () => {
  it("initializing → bootstrap", () => {
    expect(resolveDestination(baseSnapshot({ bootstrap: "initializing" }))).toEqual({ tree: "Bootstrap" });
  });

  it("ready + unauthenticated → welcome screen", () => {
    expect(resolveDestination(baseSnapshot({ auth: "unauthenticated" }))).toEqual({
      tree: "PublicStack", screen: "Welcome",
    });
  });

  it("authenticated customer → customer app stack", () => {
    expect(resolveDestination(baseSnapshot())).toEqual({ tree: "CustomerAppStack", pendingDeepLink: undefined });
  });

  it("invalid audience (staff token) → invalid-access state, never customer tabs", () => {
    const dest = resolveDestination(baseSnapshot({ auth: "invalid_audience", audience: "serviceos:staff" }));
    expect(dest).toEqual({ tree: "ExceptionalStateStack", screen: "InvalidAccess", reason: "invalid_audience" });
  });

  it("session expired → session-expired screen", () => {
    expect(resolveDestination(baseSnapshot({ auth: "session_expired" }))).toEqual({
      tree: "ExceptionalStateStack", screen: "SessionExpired", reason: "session_expired",
    });
  });

  it("suspended account → suspended screen", () => {
    expect(resolveDestination(baseSnapshot({ account: "suspended" }))).toEqual({
      tree: "ExceptionalStateStack", screen: "AccountSuspended", reason: "suspended",
    });
  });

  it("forced update → update-required screen", () => {
    expect(resolveDestination(baseSnapshot({ appVersion: "update_required" }))).toEqual({
      tree: "ExceptionalStateStack", screen: "UpdateRequired", reason: "update_required",
    });
  });

  it("maintenance → maintenance screen", () => {
    expect(resolveDestination(baseSnapshot({ platform: "maintenance" }))).toEqual({
      tree: "ExceptionalStateStack", screen: "Maintenance", reason: "maintenance",
    });
  });

  it("storage failure → storage-unavailable screen", () => {
    expect(resolveDestination(baseSnapshot({ storage: "unavailable" }))).toEqual({
      tree: "ExceptionalStateStack", screen: "StorageUnavailable", reason: "unavailable",
    });
  });

  it("disabled vertical deep link → vertical-unavailable screen", () => {
    const dest = resolveDestination(
      baseSnapshot({
        pendingDeepLink: { routeKey: "vertical.selected", params: { vertical: "coaching" }, validated: true },
      }),
    );
    expect(dest).toEqual({ tree: "ExceptionalStateStack", screen: "VerticalUnavailable", reason: "vertical_disabled" });
  });

  it("valid authenticated deep link → authorized destination carrying the link", () => {
    const pendingDeepLink = { routeKey: "booking.detail", params: { bookingId: "b-1" }, validated: true };
    expect(resolveDestination(baseSnapshot({ pendingDeepLink }))).toEqual({
      tree: "CustomerAppStack", pendingDeepLink,
    });
  });

  it("malformed/rejected deep link → safe fallback (plain customer shell, no crash)", () => {
    const pendingDeepLink = { routeKey: "booking.detail", params: {}, validated: false, rejectedReason: "malformed_params" as const };
    expect(resolveDestination(baseSnapshot({ pendingDeepLink }))).toEqual({ tree: "CustomerAppStack" });
  });
});

describe("resolveDestination — guard precedence (competing states)", () => {
  it("forced update wins over an authenticated session", () => {
    const dest = resolveDestination(baseSnapshot({ appVersion: "update_required", auth: "authenticated_customer" }));
    expect(dest.tree).toBe("ExceptionalStateStack");
    expect((dest as { screen: string }).screen).toBe("UpdateRequired");
  });

  it("suspended account wins over a pending deep link", () => {
    const dest = resolveDestination(
      baseSnapshot({
        account: "suspended",
        pendingDeepLink: { routeKey: "booking.detail", params: { bookingId: "b-1" }, validated: true },
      }),
    );
    expect((dest as { screen: string }).screen).toBe("AccountSuspended");
  });

  it("session expired wins over a cached-looking tab state (no bootstrap short-circuit)", () => {
    const dest = resolveDestination(baseSnapshot({ auth: "session_expired", bootstrap: "ready" }));
    expect((dest as { screen: string }).screen).toBe("SessionExpired");
  });

  it("maintenance wins over a notification deep link", () => {
    const dest = resolveDestination(
      baseSnapshot({
        platform: "maintenance",
        pendingDeepLink: { routeKey: "notification.destination", params: { notificationId: "n-1" }, validated: true },
      }),
    );
    expect((dest as { screen: string }).screen).toBe("Maintenance");
  });

  it("storage failure wins over authentication", () => {
    const dest = resolveDestination(baseSnapshot({ storage: "unavailable", auth: "authenticated_customer" }));
    expect((dest as { screen: string }).screen).toBe("StorageUnavailable");
  });

  it("disabled vertical wins over an otherwise-valid customer session for that specific deep link only", () => {
    const dest = resolveDestination(
      baseSnapshot({
        auth: "authenticated_customer",
        pendingDeepLink: { routeKey: "vertical.selected", params: { vertical: "real_estate" }, validated: true },
        enabledVerticals: { enabled: ["home_services"] },
      }),
    );
    expect((dest as { screen: string }).screen).toBe("VerticalUnavailable");
  });
});

describe("destinationSignature", () => {
  it("differs across trees and exceptional-state screens", () => {
    const a = destinationSignature({ tree: "CustomerAppStack" });
    const b = destinationSignature({ tree: "ExceptionalStateStack", screen: "SessionExpired", reason: "x" });
    const c = destinationSignature({ tree: "ExceptionalStateStack", screen: "Maintenance", reason: "x" });
    expect(new Set([a, b, c]).size).toBe(3);
  });
});
