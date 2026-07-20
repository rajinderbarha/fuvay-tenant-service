import { resolveNotificationIntent, __resetNotificationIntentDedupeForTests } from "../notification-intent";

describe("resolveNotificationIntent", () => {
  afterEach(() => __resetNotificationIntentDedupeForTests());

  it("accepts a notification-enabled route with valid params", () => {
    const result = resolveNotificationIntent({
      notificationId: "n1",
      type: "booking_update",
      route: "bookingDetail",
      params: { bookingId: "abc-123" },
      receivedAt: "2026-01-01T00:00:00.000Z",
    });
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.routeId).toBe("bookingDetail");
  });

  it("rejects a route not in the compiled registry", () => {
    const result = resolveNotificationIntent({ notificationId: "n2", type: "x", route: "totally-made-up", params: {}, receivedAt: "2026-01-01T00:00:00.000Z" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("route_not_allowlisted");
  });

  it("rejects a route that exists but is not notification-eligible", () => {
    const result = resolveNotificationIntent({ notificationId: "n3", type: "x", route: "home", params: {}, receivedAt: "2026-01-01T00:00:00.000Z" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("route_not_allowlisted");
  });

  it("rejects an expired intent", () => {
    const result = resolveNotificationIntent(
      {
        notificationId: "n4",
        type: "x",
        route: "bookingDetail",
        params: { bookingId: "a" },
        receivedAt: "2026-01-01T00:00:00.000Z",
        expiresAt: "2026-01-01T00:00:01.000Z",
      },
      "2026-01-02T00:00:00.000Z"
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("expired");
  });

  it("rejects malformed param values", () => {
    const result = resolveNotificationIntent({
      notificationId: "n5",
      type: "x",
      route: "bookingDetail",
      params: { bookingId: "<script>alert(1)</script>" },
      receivedAt: "2026-01-01T00:00:00.000Z",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("malformed_params");
  });

  it("rejects a duplicate notification id (consume-once)", () => {
    const intent = { notificationId: "n6", type: "x", route: "bookingDetail", params: { bookingId: "a" }, receivedAt: "2026-01-01T00:00:00.000Z" };
    expect(resolveNotificationIntent(intent).ok).toBe(true);
    const second = resolveNotificationIntent(intent);
    expect(second.ok).toBe(false);
    if (!second.ok) expect(second.reason).toBe("duplicate");
  });
});
