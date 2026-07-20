import { z } from "zod";

/**
 * Mirrors the real response of
 * `GET /v1/customer/bookings/{bookingId}/tracking` — a genuine,
 * append-only lifecycle timeline built from `ServiceJobAssignmentEvent`
 * rows, already mapped to customer-safe labels server-side
 * (`_safe_event_label`) — see CUSTOMER-L5-12-timeline-contract.md. The
 * first item is always a synthetic, timestamp-less "Booking confirmed"
 * row (`event_type`/`created_at` both absent) — real backend behavior,
 * not a client-side fabrication.
 */
export const timelineItemSchema = z.object({
  event: z.string().min(1),
  event_type: z.string().optional(),
  created_at: z.string().nullable().optional(),
  status: z.string().optional(),
});
export type ValidatedTimelineItem = z.infer<typeof timelineItemSchema>;

const bookingTrackingResponseSchema = z.object({
  booking_number: z.string().min(1),
  status: z.string().min(1),
  assignment_status: z.string().min(1),
  assignment_message: z.string(),
  timeline: z.array(z.unknown()),
});

export interface BookingTrackingResult {
  bookingNumber: string;
  status: string;
  assignmentStatus: string;
  assignmentMessage: string;
  timeline: ValidatedTimelineItem[];
  droppedCount: number;
}

/** Drops individually-invalid timeline rows rather than failing the whole screen — same resilience pattern used throughout this app. */
export function parseBookingTracking(payload: unknown): BookingTrackingResult | null {
  const envelope = bookingTrackingResponseSchema.safeParse(payload);
  if (!envelope.success) return null;

  const timeline: ValidatedTimelineItem[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.timeline) {
    const parsed = timelineItemSchema.safeParse(raw);
    if (parsed.success) timeline.push(parsed.data);
    else droppedCount += 1;
  }
  return {
    bookingNumber: envelope.data.booking_number,
    status: envelope.data.status,
    assignmentStatus: envelope.data.assignment_status,
    assignmentMessage: envelope.data.assignment_message,
    timeline,
    droppedCount,
  };
}
