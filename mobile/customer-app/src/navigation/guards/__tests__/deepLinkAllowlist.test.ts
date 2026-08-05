import { validateDeepLink } from "../deepLinkAllowlist";

const enabledHomeServices = { enabled: ["home_services" as const] };

describe("validateDeepLink", () => {
  it("accepts a well-formed, authenticated, allowlisted route", () => {
    const result = validateDeepLink({
      routeKey: "booking.detail",
      params: { bookingId: "b-1" },
      isAuthenticated: true,
      audience: "serviceos:customer",
      enabledVerticals: enabledHomeServices,
    });
    expect(result.validated).toBe(true);
  });

  it("rejects an unknown route instead of guessing a destination", () => {
    const result = validateDeepLink({
      routeKey: "not.a.real.route",
      params: {},
      isAuthenticated: true,
      audience: "serviceos:customer",
      enabledVerticals: enabledHomeServices,
    });
    expect(result.validated).toBe(false);
    expect(result.rejectedReason).toBe("unknown_route");
  });

  it("rejects any staff/tenant/admin/provider/technician-prefixed route unconditionally", () => {
    for (const routeKey of ["staff.jobDetail", "tenant.dashboard", "admin.customers", "provider.payout", "technician.schedule"]) {
      const result = validateDeepLink({
        routeKey, params: {}, isAuthenticated: true, audience: "serviceos:customer", enabledVerticals: enabledHomeServices,
      });
      expect(result.validated).toBe(false);
      expect(result.rejectedReason).toBe("unknown_route");
    }
  });

  it("rejects a route missing a required param without crashing", () => {
    const result = validateDeepLink({
      routeKey: "booking.detail", params: {}, isAuthenticated: true, audience: "serviceos:customer", enabledVerticals: enabledHomeServices,
    });
    expect(result.validated).toBe(false);
    expect(result.rejectedReason).toBe("malformed_params");
  });

  it("rejects an auth-required route when unauthenticated", () => {
    const result = validateDeepLink({
      routeKey: "booking.detail", params: { bookingId: "b-1" }, isAuthenticated: false, audience: null, enabledVerticals: enabledHomeServices,
    });
    expect(result.rejectedReason).toBe("requires_auth");
  });

  it("rejects a non-customer audience even if otherwise well-formed", () => {
    const result = validateDeepLink({
      routeKey: "booking.detail", params: { bookingId: "b-1" }, isAuthenticated: true, audience: "serviceos:staff", enabledVerticals: enabledHomeServices,
    });
    expect(result.rejectedReason).toBe("wrong_audience");
  });

  it("rejects a route scoped to a disabled vertical", () => {
    const result = validateDeepLink({
      routeKey: "quote.review", params: { quoteId: "q-1" }, isAuthenticated: true, audience: "serviceos:customer", enabledVerticals: { enabled: [] },
    });
    expect(result.rejectedReason).toBe("vertical_disabled");
  });

  it("never throws for a malformed payload -- always returns an inert PendingDeepLink", () => {
    expect(() =>
      validateDeepLink({
        routeKey: "", params: {}, isAuthenticated: true, audience: "serviceos:customer", enabledVerticals: enabledHomeServices,
      }),
    ).not.toThrow();
  });
});
