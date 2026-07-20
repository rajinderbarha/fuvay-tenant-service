import { setPendingDestination, consumePendingDestination, peekPendingDestination, clearPendingDestination } from "../pending-deep-link-store";

describe("pending-deep-link-store", () => {
  afterEach(() => clearPendingDestination());

  it("stores and consumes exactly once", () => {
    setPendingDestination({ routeId: "home", params: {}, source: "custom-scheme", requiresAuth: false, requiresMarketplace: false });
    const first = consumePendingDestination();
    expect(first?.routeId).toBe("home");
    const second = consumePendingDestination();
    expect(second).toBeNull();
  });

  it("peek does not consume", () => {
    setPendingDestination({ routeId: "home", params: {}, source: "custom-scheme", requiresAuth: false, requiresMarketplace: false });
    expect(peekPendingDestination()?.routeId).toBe("home");
    expect(peekPendingDestination()?.routeId).toBe("home");
  });

  it("expires after the TTL", () => {
    const receivedAt = "2026-01-01T00:00:00.000Z";
    setPendingDestination({ routeId: "home", params: {}, source: "custom-scheme", requiresAuth: false, requiresMarketplace: false }, receivedAt);
    const muchLater = "2026-01-01T01:00:00.000Z"; // 1 hour later, past the 5-minute TTL
    expect(consumePendingDestination(muchLater)).toBeNull();
  });

  it("clear removes the pending destination", () => {
    setPendingDestination({ routeId: "home", params: {}, source: "custom-scheme", requiresAuth: false, requiresMarketplace: false });
    clearPendingDestination();
    expect(peekPendingDestination()).toBeNull();
  });
});
