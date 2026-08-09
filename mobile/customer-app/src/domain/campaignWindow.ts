/**
 * When a limited-time campaign stops.
 *
 * The rule this file exists to hold: the app never manufactures urgency. It
 * states a real end date the backend set, and says nothing at all when there
 * isn't one. No countdown timers, no "hurry -- ends soon" on an open-ended
 * campaign, no "last day!" derived by rounding. A customer who catches one
 * invented deadline discounts every other claim on the screen.
 */

/** "Ends today" / "Ends tomorrow" / "Ends 5 Nov". Null when the campaign has no
 * end date, or the value cannot be parsed -- an unparseable date is not a
 * deadline worth guessing at. */
export function formatCampaignEnds(endsAt: string | null, now: Date = new Date()): string | null {
  if (!endsAt) return null;
  const end = new Date(endsAt);
  if (Number.isNaN(end.getTime())) return null;

  // Compared by calendar day, not by elapsed hours: a campaign ending at 23:59
  // tonight "ends today" even though that is 8 hours away, and one ending at
  // 00:30 tomorrow does not.
  const days = calendarDaysBetween(now, end);
  if (days < 0) return null;          // already over; the backend filters these out too
  if (days === 0) return "Ends today";
  if (days === 1) return "Ends tomorrow";
  return `Ends ${end.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
}

function calendarDaysBetween(from: Date, to: Date): number {
  const a = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate());
  const b = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate());
  return Math.round((b - a) / 86_400_000);
}
