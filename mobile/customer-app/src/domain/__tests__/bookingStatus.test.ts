import { interpretBookingStatus, resolveTimelineStepState, RECEIPT_TIMELINE_STEPS, BookingReceiptStage } from "../bookingStatus";

// Every real value confirmed written onto ServiceBooking.status across
// BOTH final_records and home_service_assignment (audit correction,
// 2026-08-01) -- `accepted`/`scheduled` are real JOB_STATUS_* values the
// job-assignment engine writes directly, not documented in
// final_records/constants.py alone.
const ALL_BOOKING_STATUSES = ["pending_assignment", "assigned", "accepted", "scheduled", "in_progress", "completed", "cancelled"] as const;
const ALL_ASSIGNMENT_STATUSES = ["unassigned", "assigned", "accepted", "rejected", "cancelled"] as const;

function expectedStage(status: string, assignmentStatus: string): BookingReceiptStage {
  if (status === "pending_assignment" && assignmentStatus === "unassigned") return "provider_assignment";
  if (status === "assigned") return "provider_assigned";
  return "unknown"; // includes cancelled, accepted, scheduled, in_progress, completed, and any other combo
}

describe("interpretBookingStatus -- complete (booking_status, assignment_status) matrix", () => {
  for (const status of ALL_BOOKING_STATUSES) {
    for (const assignmentStatus of ALL_ASSIGNMENT_STATUSES) {
      it(`(${status}, ${assignmentStatus}) -> ${expectedStage(status, assignmentStatus)}`, () => {
        expect(interpretBookingStatus(status, assignmentStatus).stage).toBe(expectedStage(status, assignmentStatus));
      });
    }
  }

  it("an unrecognized future booking_status always renders the neutral unknown stage, regardless of assignment_status", () => {
    for (const assignmentStatus of ALL_ASSIGNMENT_STATUSES) {
      const result = interpretBookingStatus("some_future_backend_status", assignmentStatus);
      expect(result.stage).toBe("unknown");
      expect(result.statusLabel).not.toContain("some_future_backend_status");
    }
  });
});

describe("interpretBookingStatus", () => {
  it("maps pending_assignment/unassigned to the default receipt stage with truthful copy", () => {
    const result = interpretBookingStatus("pending_assignment", "unassigned");
    expect(result.stage).toBe("provider_assignment");
    expect(result.activityText).toBe("Assigning an eligible professional");
    expect(result.supportingText).toContain("notify you when a provider accepts");
  });

  it("maps assigned to provider_assigned regardless of assignment_status value", () => {
    for (const assignmentStatus of ALL_ASSIGNMENT_STATUSES) {
      expect(interpretBookingStatus("assigned", assignmentStatus).stage).toBe("provider_assigned");
    }
  });

  it("never renders in_progress or completed as 'scheduled' or any other advanced stage -- neither is proven this phase", () => {
    expect(interpretBookingStatus("in_progress", "assigned").stage).toBe("unknown");
    expect(interpretBookingStatus("completed", "assigned").stage).toBe("unknown");
  });

  it("never renders accepted or scheduled as an advanced stage either -- real statuses this phase does not yet own", () => {
    expect(interpretBookingStatus("accepted", "accepted").stage).toBe("unknown");
    expect(interpretBookingStatus("scheduled", "assigned").stage).toBe("unknown");
  });

  it("never advances past provider_assignment without assignment_status evidence", () => {
    const result = interpretBookingStatus("pending_assignment", "unassigned");
    expect(result.stage).not.toBe("provider_assigned");
    expect(result.stage).not.toBe("scheduled");
  });

  it("maps an unrecognized status to the safe unknown stage without exposing the raw enum", () => {
    const result = interpretBookingStatus("some_future_backend_status", "unassigned");
    expect(result.stage).toBe("unknown");
    expect(result.statusLabel).not.toContain("some_future_backend_status");
  });

  it("maps cancelled to unknown with no activity text, distinct copy from a generic pending status", () => {
    const result = interpretBookingStatus("cancelled", "unassigned");
    expect(result.stage).toBe("unknown");
    expect(result.activityText).toBeNull();
    expect(result.statusLabel).toBe("Cancelled");
    expect(result.statusLabel).not.toBe(interpretBookingStatus("in_progress", "assigned").statusLabel);
  });
});

describe("resolveTimelineStepState", () => {
  it("marks request_confirmed complete once assignment is in progress", () => {
    expect(resolveTimelineStepState("request_confirmed", "provider_assignment")).toBe("complete");
  });

  it("marks provider_assignment active while pending", () => {
    expect(resolveTimelineStepState("provider_assignment", "provider_assignment")).toBe("active");
  });

  it("marks scheduled pending while still awaiting assignment", () => {
    expect(resolveTimelineStepState("scheduled", "provider_assignment")).toBe("pending");
  });

  it("never marks a later step complete without the current stage having reached it", () => {
    for (const step of RECEIPT_TIMELINE_STEPS) {
      expect(resolveTimelineStepState(step.key, "request_confirmed")).not.toBe("complete");
    }
  });

  it("an unknown current stage (e.g. in_progress/completed/cancelled) never advances the timeline past step 1", () => {
    for (const step of RECEIPT_TIMELINE_STEPS.slice(1)) {
      expect(resolveTimelineStepState(step.key, "unknown")).not.toBe("complete");
    }
  });
});
