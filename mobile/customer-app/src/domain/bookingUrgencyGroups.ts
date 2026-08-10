import { BookingUrgency, CustomerBookingListItem } from "./bookingList";

export interface BookingUrgencyGroup {
  urgency: BookingUrgency;
  /** Heading the customer reads. */
  title: string;
  /** One line under it, only where it earns its space. */
  subtitle: string | null;
  items: CustomerBookingListItem[];
}

/**
 * Splits My Bookings into what needs attention now and what does not.
 *
 * The list was strictly newest-first, so a visit that was six days overdue sat wherever
 * its booking date put it -- often pages below something scheduled for next week. Finding
 * the late ones meant reading every card.
 *
 * The grouping uses the SERVER's `urgency`, never a date compared in the app: the
 * provider's dashboard reads the same field from the same rule, and a customer being
 * told "Today" for a job the provider already calls overdue is worse than no grouping
 * at all.
 */

/**
 * Today first, then what was missed.
 *
 * Late led this list at first, which buried everything else: with 29 overdue bookings on a
 * real account, today's visits started at card 30 and a booking just made was unfindable --
 * which is exactly how it was reported ("new booked job not showing"). It was there, 29
 * cards down.
 *
 * Lateness is not hidden by this: the red summary line above the tabs states the count
 * before any scrolling, and the group keeps its own heading and colour. What changes is
 * that a long backlog no longer pushes the present out of view.
 */
const ORDER: BookingUrgency[] = ["today", "late", "upcoming", "unscheduled"];

const HEADINGS: Record<BookingUrgency, { title: string; subtitle: string | null }> = {
  // Named for what happened, not for blame: the slot passed. Whether that is the
  // provider's fault is not something this screen knows.
  late: { title: "Past their slot", subtitle: "These were due earlier and have not been completed." },
  today: { title: "Today", subtitle: null },
  upcoming: { title: "Upcoming", subtitle: null },
  // A booking nobody has scheduled yet is not "upcoming" -- there is nothing to be up
  // and coming. Saying so is more honest than implying a date exists.
  unscheduled: { title: "Waiting to be scheduled", subtitle: "We'll confirm a visit time with you." },
};

/**
 * Groups in a fixed order, dropping empty groups.
 *
 * Items with no urgency (finished work, or an older backend that sends none) are
 * returned in `ungrouped` rather than forced into a bucket, so the caller can render
 * them as a plain list. A completed booking is not "upcoming" and must never be filed
 * as though something is still owed.
 */
export function groupByUrgency(items: readonly CustomerBookingListItem[]): {
  groups: BookingUrgencyGroup[];
  ungrouped: CustomerBookingListItem[];
} {
  const byUrgency = new Map<BookingUrgency, CustomerBookingListItem[]>();
  const ungrouped: CustomerBookingListItem[] = [];

  for (const item of items) {
    if (!item.urgency) {
      ungrouped.push(item);
      continue;
    }
    const bucket = byUrgency.get(item.urgency);
    if (bucket) bucket.push(item);
    else byUrgency.set(item.urgency, [item]);
  }

  const groups = ORDER.flatMap(urgency => {
    const groupItems = byUrgency.get(urgency);
    if (!groupItems || groupItems.length === 0) return [];
    return [{ urgency, ...HEADINGS[urgency], items: groupItems }];
  });

  return { groups, ungrouped };
}

/** How many need attention right now. Drives the one-line summary at the top; zero
 * means the summary is not rendered at all rather than saying "0 late". */
export function countLate(items: readonly CustomerBookingListItem[]): number {
  return items.filter(item => item.urgency === "late").length;
}
