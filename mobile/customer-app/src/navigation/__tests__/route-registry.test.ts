import { ROUTE_REGISTRY } from "../route-registry";

describe("route-registry — CUSTOMER-L5-05 booking-assistant promotion", () => {
  it("bookingAssistant is a real, always-on authenticated route (no longer dev-only)", () => {
    expect(ROUTE_REGISTRY.bookingAssistant.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bookingAssistant.productionEnabled).toBe(true);
    expect(ROUTE_REGISTRY.bookingAssistant.featureKey).toBeUndefined();
  });
});

describe("route-registry — CUSTOMER-L5-06 booking-draft/media promotion", () => {
  it("bookingDraft and bookingMedia are real, always-on authenticated routes", () => {
    expect(ROUTE_REGISTRY.bookingDraft.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bookingDraft.productionEnabled).toBe(true);
    expect(ROUTE_REGISTRY.bookingMedia.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bookingMedia.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-07 address/serviceability promotion", () => {
  it("addressSelection, addressForm and serviceabilityCheck are real, always-on authenticated routes", () => {
    for (const id of ["addressSelection", "addressForm", "serviceabilityCheck"] as const) {
      expect(ROUTE_REGISTRY[id].access).toBe("authenticated");
      expect(ROUTE_REGISTRY[id].productionEnabled).toBe(true);
    }
  });
});

describe("route-registry — CUSTOMER-L5-08 providerPreview promotion", () => {
  it("providerPreview is a real, always-on authenticated route (no longer dev-only)", () => {
    expect(ROUTE_REGISTRY.providerPreview.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.providerPreview.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-09 pricing promotion", () => {
  it("pricing is a real, always-on authenticated route (no longer dev-only)", () => {
    expect(ROUTE_REGISTRY.pricing.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.pricing.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-10 bargain promotion", () => {
  it("bargain is a real, always-on authenticated route (no longer dev-only)", () => {
    expect(ROUTE_REGISTRY.bargain.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bargain.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-11 bookingReview/bookingSuccess promotion", () => {
  it("bookingReview and bookingSuccess are real, always-on routes (no longer dev-only)", () => {
    expect(ROUTE_REGISTRY.bookingReview.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bookingReview.productionEnabled).toBe(true);
    expect(ROUTE_REGISTRY.bookingSuccess.access).toBe("booking-owner-required");
    expect(ROUTE_REGISTRY.bookingSuccess.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-12 bookingsList/bookingDetail promotion", () => {
  it("bookingsList and bookingDetail are real, always-on routes (no longer dev-only), unrelated to the legacy /v1/bookings screens", () => {
    expect(ROUTE_REGISTRY.bookingsList.access).toBe("authenticated");
    expect(ROUTE_REGISTRY.bookingsList.productionEnabled).toBe(true);
    expect(ROUTE_REGISTRY.bookingDetail.access).toBe("booking-owner-required");
    expect(ROUTE_REGISTRY.bookingDetail.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-13 tracking promotion", () => {
  it("tracking is a real, always-on route (no longer dev-only) — a non-map, status-milestone experience, not live GPS (see CUSTOMER-L5-13-baseline-verification.md)", () => {
    expect(ROUTE_REGISTRY.tracking.access).toBe("booking-owner-required");
    expect(ROUTE_REGISTRY.tracking.productionEnabled).toBe(true);
  });
});

describe("route-registry — CUSTOMER-L5-14 quoteDecision", () => {
  it("quoteDecision is a real, always-on route — the real customer-facing quote_checklist decision flow, not the orphaned execution-engine PartsRequest state (see CUSTOMER-L5-14-baseline-verification.md)", () => {
    expect(ROUTE_REGISTRY.quoteDecision.access).toBe("booking-owner-required");
    expect(ROUTE_REGISTRY.quoteDecision.productionEnabled).toBe(true);
  });
});
