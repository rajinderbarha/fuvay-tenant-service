import { z } from "zod";

/**
 * Mirrors the real, already-customer-safe response of
 * `GET /v1/customer/bookings` (`app/engines/home_service_assignment/customer_router.py`)
 * — see CUSTOMER-L5-12-contract-matrix.md. `selected_provider` is already
 * stripped server-side to exactly 3 fields by `_customer_safe_provider()`
 * — no internal-score stripping is needed client-side here (unlike
 * CUSTOMER-L5-11's `final_records` field, which required client-side
 * stripping).
 */
const listItemProviderSchema = z.object({
  provider_name: z.string().nullable(),
  rating: z.number().nullable(),
  public_badges: z.array(z.string()),
});

export const bookingListItemSchema = z.object({
  booking_id: z.string().min(1),
  booking_number: z.string().min(1),
  status: z.string().min(1),
  issue_summary: z.string().nullable(),
  city: z.string().nullable(),
  preferred_date: z.string().nullable(),
  selected_provider: listItemProviderSchema.nullable(),
  selected_price_option: z.string().nullable().optional(),
  selected_price_amount: z.number().nullable().optional(),
});
export type ValidatedBookingListItem = z.infer<typeof bookingListItemSchema>;

const bookingListResponseSchema = z.object({
  items: z.array(z.unknown()),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
});

export interface BookingListPageResult {
  items: ValidatedBookingListItem[];
  page: number;
  pageSize: number;
  droppedCount: number;
  /** No real `total`/`has_more` field exists — inferred honestly from a full page, never fabricated (CUSTOMER-L5-12-contract-matrix.md). */
  mayHaveMore: boolean;
}

/** Drops individually-invalid rows rather than failing the whole page — the same resilience pattern used throughout this app since CUSTOMER-L5-03. */
export function parseBookingListPage(payload: unknown): BookingListPageResult | null {
  const envelope = bookingListResponseSchema.safeParse(payload);
  if (!envelope.success) return null;

  const items: ValidatedBookingListItem[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.items) {
    const parsed = bookingListItemSchema.safeParse(raw);
    if (parsed.success) items.push(parsed.data);
    else droppedCount += 1;
  }
  return {
    items,
    page: envelope.data.page,
    pageSize: envelope.data.page_size,
    droppedCount,
    mayHaveMore: envelope.data.items.length >= envelope.data.page_size,
  };
}
