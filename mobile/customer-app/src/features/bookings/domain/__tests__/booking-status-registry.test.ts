import { resolveBookingStatus, isKnownBookingStatus } from "../booking-status-registry";

describe("resolveBookingStatus", () => {
  it("maps every real, reachable status to a real title and correct group", () => {
    expect(resolveBookingStatus("pending_assignment")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("assigned")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("accepted")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("scheduled")).toMatchObject({ group: "active", terminal: false });
  });

  it("maps completed/cancelled correctly — confirmed real and reachable via the execution engine (CUSTOMER-L5-13), not merely defined-but-dead constants", () => {
    expect(resolveBookingStatus("completed")).toMatchObject({ group: "past", terminal: true, success: true });
    expect(resolveBookingStatus("cancelled")).toMatchObject({ group: "past", terminal: true, success: false, warning: true });
  });

  it("maps every real execution-engine status added this sprint (CUSTOMER-L5-13)", () => {
    expect(resolveBookingStatus("on_the_way")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("reached_site")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("inspection_started")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("inspection_done")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("quote_required")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("service_started")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("work_done")).toMatchObject({ group: "active", terminal: false });
    expect(resolveBookingStatus("customer_not_available")).toMatchObject({ group: "active", terminal: false, warning: true });
  });

  it("maps every real quote_checklist-engine status added this sprint (CUSTOMER-L5-14) — a separate real engine that also writes to ServiceJob.status", () => {
    expect(resolveBookingStatus("awaiting_customer_quote_approval")).toMatchObject({ group: "active", terminal: false, warning: true });
    expect(resolveBookingStatus("quote_approved")).toMatchObject({ group: "active", terminal: false, success: true });
    expect(resolveBookingStatus("quote_rejected")).toMatchObject({ group: "active", terminal: false, warning: true });
    expect(resolveBookingStatus("quote_revision_requested")).toMatchObject({ group: "active", terminal: false, warning: true });
  });

  it("fails safe on an unrecognized status: never defaults to completed/terminal/success", () => {
    const result = resolveBookingStatus("some_future_status_this_client_has_never_seen");
    expect(result.terminal).toBe(false);
    expect(result.success).toBe(false);
    expect(result.group).toBe("active");
    expect(result.titleKey).toBe("bookings.status.processing");
  });
});

describe("isKnownBookingStatus", () => {
  it("returns true for real statuses and false for unrecognized ones", () => {
    expect(isKnownBookingStatus("pending_assignment")).toBe(true);
    expect(isKnownBookingStatus("totally_made_up")).toBe(false);
  });
});
