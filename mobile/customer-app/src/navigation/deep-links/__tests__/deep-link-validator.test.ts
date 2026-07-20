import { validateDeepLink } from "../deep-link-validator";
import { parseDeepLink } from "../deep-link-parser";

function link(url: string) {
  const parsed = parseDeepLink(url);
  if (!parsed.ok) throw new Error("test setup: expected a parseable URL");
  return parsed.link;
}

describe("validateDeepLink", () => {
  it("accepts a valid, allowlisted public route", () => {
    const result = validateDeepLink(link("serviceos://home"));
    expect(result.ok).toBe(true);
  });

  it("accepts a valid parameterized route with a well-formed id", () => {
    const result = validateDeepLink(link("serviceos://bookings/abc-123"));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.destination.params.bookingId).toBe("abc-123");
  });

  it("rejects an unknown scheme/host", () => {
    const result = validateDeepLink(link("https://evil.example.com/home"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("unknown_scheme_or_host");
  });

  it("rejects an unknown path", () => {
    const result = validateDeepLink(link("serviceos://not-a-real-page"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("unknown_path");
  });

  it("rejects a malformed id in a parameterized route", () => {
    const result = validateDeepLink(link("serviceos://bookings/<script>"));
    expect(result.ok).toBe(false);
  });

  it("rejects an unexpected query field", () => {
    const result = validateDeepLink(link("serviceos://home?evil=1"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("unexpected_query_field");
  });

  it("rejects a token-like query field even if otherwise allowlisted-shaped", () => {
    const result = validateDeepLink(link("serviceos://home?access_token=abc"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("token_like_query_rejected");
  });

  it("rejects a nested redirect URL in a query value", () => {
    const result = validateDeepLink(link("serviceos://home?src=https://evil.example.com"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("nested_redirect_rejected");
  });

  it("rejects an expired campaign link", () => {
    const pastTimestamp = Math.floor(new Date("2020-01-01T00:00:00.000Z").getTime() / 1000);
    const result = validateDeepLink(link(`serviceos://home?exp=${pastTimestamp}`), { nowIso: "2026-01-01T00:00:00.000Z" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("expired_link");
  });

  it("accepts a non-expired campaign link", () => {
    const futureTimestamp = Math.floor(new Date("2027-01-01T00:00:00.000Z").getTime() / 1000);
    const result = validateDeepLink(link(`serviceos://home?exp=${futureTimestamp}`), { nowIso: "2026-01-01T00:00:00.000Z" });
    expect(result.ok).toBe(true);
  });

  it("accepts a category deep link with a well-formed id", () => {
    const result = validateDeepLink(link("serviceos://categories/cat-123"));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.destination.routeId).toBe("categoryDetail");
      expect(result.destination.params.categoryId).toBe("cat-123");
    }
  });

  it("accepts a service deep link with both category and service ids", () => {
    const result = validateDeepLink(link("serviceos://categories/cat-123/services/svc-456"));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.destination.routeId).toBe("serviceDetails");
      expect(result.destination.params.categoryId).toBe("cat-123");
      expect(result.destination.params.serviceId).toBe("svc-456");
    }
  });

  it("rejects a service deep link missing the category segment", () => {
    const result = validateDeepLink(link("serviceos://services/svc-456"));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("unknown_path");
  });

  it("rejects a category deep link with a malformed id", () => {
    const result = validateDeepLink(link("serviceos://categories/<script>"));
    expect(result.ok).toBe(false);
  });

  it("accepts the search deep link", () => {
    const result = validateDeepLink(link("serviceos://search"));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.destination.routeId).toBe("search");
  });

  it("rejects a cross-marketplace destination", () => {
    const result = validateDeepLink(link("serviceos://home"), { marketplaceId: "default", linkMarketplaceId: "other" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("cross_marketplace_rejected");
  });
});
