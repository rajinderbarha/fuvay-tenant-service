import { groupByUrgency, countLate } from "../bookingUrgencyGroups";
import { CustomerBookingListItem, BookingUrgency } from "../bookingList";

function booking(id: string, urgency: BookingUrgency | null): CustomerBookingListItem {
  return {
    bookingId: id, bookingNumber: id, rawStatus: "confirmed",
    stage: "active" as never, statusLabel: "Request confirmed",
    activityText: null, supportingText: null, createdAt: null,
    serviceName: "AC Repair", jobType: null, summaryFields: [],
    address: { label: null, formatted: "Ludhiana", zipcode: null },
    pricing: { state: { kind: "unavailable" }, inspection: null },
    urgency, scheduledDate: null, scheduledTimeWindow: null, latenessLabel: null,
  };
}

describe("groupByUrgency", () => {
  it("puts what is past its slot first, whatever order the list arrived in", () => {
    // The list was strictly newest-first, so a six-day-overdue visit sat wherever its
    // booking date put it -- often below something scheduled for next week. Finding the
    // late ones meant reading every card.
    const { groups } = groupByUrgency([
      booking("upcoming-1", "upcoming"),
      booking("late-1", "late"),
      booking("today-1", "today"),
    ]);
    expect(groups.map(g => g.urgency)).toEqual(["late", "today", "upcoming"]);
  });

  it("keeps each group in the order the server sent it", () => {
    const { groups } = groupByUrgency([
      booking("late-1", "late"), booking("late-2", "late"), booking("today-1", "today"),
    ]);
    expect(groups[0].items.map(i => i.bookingId)).toEqual(["late-1", "late-2"]);
  });

  it("omits groups with nothing in them", () => {
    // A heading over no cards is a claim that there is something there.
    const { groups } = groupByUrgency([booking("today-1", "today")]);
    expect(groups.map(g => g.urgency)).toEqual(["today"]);
  });

  it("does not force finished bookings into a group", () => {
    // A completed booking is not "upcoming", and filing it as one implies something is
    // still owed. It comes back ungrouped so the Completed tab stays a plain list.
    const { groups, ungrouped } = groupByUrgency([
      booking("done-1", null), booking("late-1", "late"),
    ]);
    expect(groups.map(g => g.urgency)).toEqual(["late"]);
    expect(ungrouped.map(i => i.bookingId)).toEqual(["done-1"]);
  });

  it("treats an older backend that sends no urgency as ungrouped, not as upcoming", () => {
    const { groups, ungrouped } = groupByUrgency([booking("a", null), booking("b", null)]);
    expect(groups).toEqual([]);
    expect(ungrouped).toHaveLength(2);
  });

  it("separates unscheduled from upcoming", () => {
    // There is nothing up and coming about a booking nobody has scheduled. Saying so is
    // more honest than implying a date exists.
    const { groups } = groupByUrgency([
      booking("u-1", "unscheduled"), booking("up-1", "upcoming"),
    ]);
    expect(groups.map(g => g.urgency)).toEqual(["upcoming", "unscheduled"]);
    expect(groups.find(g => g.urgency === "unscheduled")?.title).toBe("Waiting to be scheduled");
  });

  it("names the late group for what happened, not for blame", () => {
    // The slot passed. Whether that is the provider's fault is not something this
    // screen knows.
    const { groups } = groupByUrgency([booking("late-1", "late")]);
    expect(groups[0].title).toBe("Past their slot");
  });

  it("handles an empty list", () => {
    expect(groupByUrgency([])).toEqual({ groups: [], ungrouped: [] });
  });
});

describe("countLate", () => {
  it("counts only what is past its slot", () => {
    expect(countLate([
      booking("l1", "late"), booking("l2", "late"),
      booking("t", "today"), booking("d", null),
    ])).toBe(2);
  });

  it("returns zero rather than something to render", () => {
    // The summary line is hidden at zero -- "0 past their slot" is noise.
    expect(countLate([booking("t", "today")])).toBe(0);
  });
});
