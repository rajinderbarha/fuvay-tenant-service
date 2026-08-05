import { resolveSafeNotificationDestination } from "../notificationDestination";
import { resolveCustomerNotificationType } from "../notificationTypeMapping";

describe("resolveSafeNotificationDestination", () => {
  it("resolves service_bookings to a BookingDetails destination", () => {
    expect(resolveSafeNotificationDestination("service_bookings", "b-1")).toEqual({
      kind: "booking", bookingId: "b-1",
    });
  });

  it("resolves customer_complaints to a SupportRequestDetails destination", () => {
    expect(resolveSafeNotificationDestination("customer_complaints", "c-1")).toEqual({
      kind: "supportRequest", requestId: "c-1",
    });
  });

  it("returns null for a real but unsupported record type (no matching customer-app screen)", () => {
    expect(resolveSafeNotificationDestination("service_invoices", "i-1")).toBeNull();
    expect(resolveSafeNotificationDestination("service_job_quote", "q-1")).toBeNull();
    expect(resolveSafeNotificationDestination("customer_review", "r-1")).toBeNull();
    expect(resolveSafeNotificationDestination("chat_thread", "t-1")).toBeNull();
  });

  it("returns null when the id is missing, even for a supported type", () => {
    expect(resolveSafeNotificationDestination("service_bookings", null)).toBeNull();
  });

  it("returns null for an unknown/malformed record type", () => {
    expect(resolveSafeNotificationDestination("something_unexpected", "x-1")).toBeNull();
    expect(resolveSafeNotificationDestination(null, "x-1")).toBeNull();
  });
});

describe("resolveCustomerNotificationType", () => {
  it("maps every known real customer-facing type to a specific icon", () => {
    expect(resolveCustomerNotificationType("booking.confirmed").icon).toBe("briefcase-outline");
    expect(resolveCustomerNotificationType("complaint.resolved").icon).toBe("shield-checkmark-outline");
  });

  it("falls back to a neutral bell icon for an unknown type, never exposing the raw type", () => {
    expect(resolveCustomerNotificationType("some.future.type").icon).toBe("notifications-outline");
  });
});
