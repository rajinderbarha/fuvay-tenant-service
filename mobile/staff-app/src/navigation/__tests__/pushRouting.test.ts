import { resolvePushRoute, resetSeenNotifications, SUPPORTED_PUSH_SCHEMA_VERSION, PushNotificationPayload } from "../pushRouting";

function payload(overrides: Partial<PushNotificationPayload> = {}): PushNotificationPayload {
  return {
    schemaVersion: SUPPORTED_PUSH_SCHEMA_VERSION,
    notificationId: "n1",
    eventType: "job_assigned",
    routeKey: "JOB_DETAIL",
    entityId: "j1",
    ...overrides,
  };
}

describe("resolvePushRoute", () => {
  beforeEach(() => resetSeenNotifications());

  it("resolves a valid job-route push", () => {
    const result = resolvePushRoute(payload());
    expect(result).toEqual({ ok: true, route: { routeKey: "JOB_DETAIL", jobId: "j1", targetAction: undefined, notificationId: "n1" } });
  });

  it("resolves a valid non-job-route push", () => {
    const result = resolvePushRoute(payload({ routeKey: "NOTIFICATIONS", entityId: undefined }));
    expect(result).toEqual({ ok: true, route: { routeKey: "NOTIFICATIONS", jobId: undefined, targetAction: undefined, notificationId: "n1" } });
  });

  it("rejects an unsupported schema version", () => {
    const result = resolvePushRoute(payload({ schemaVersion: 99 }));
    expect(result).toEqual({ ok: false, reason: "UNSUPPORTED_SCHEMA_VERSION" });
  });

  it("rejects an unknown routeKey (fails closed, never falls back to a raw URL)", () => {
    const result = resolvePushRoute(payload({ routeKey: "SOME_MADE_UP_ROUTE" }));
    expect(result).toEqual({ ok: false, reason: "ROUTE_NOT_FOUND" });
  });

  it("rejects a job route missing its entityId", () => {
    const result = resolvePushRoute(payload({ entityId: undefined }));
    expect(result).toEqual({ ok: false, reason: "ROUTE_NOT_FOUND" });
  });

  it("treats a duplicate notificationId tap as a no-op", () => {
    const first = resolvePushRoute(payload());
    expect(first.ok).toBe(true);
    const second = resolvePushRoute(payload());
    expect(second).toEqual({ ok: false, reason: "DUPLICATE_NOTIFICATION" });
  });

  it("allows the same notificationId again after resetSeenNotifications (new app session)", () => {
    resolvePushRoute(payload());
    resetSeenNotifications();
    const result = resolvePushRoute(payload());
    expect(result.ok).toBe(true);
  });
});
