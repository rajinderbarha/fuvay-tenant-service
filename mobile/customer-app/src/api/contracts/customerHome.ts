/**
 * DTO for GET /v1/customer/home (app/engines/customer_home/router.py +
 * service.py, dated 2026-08-01, read directly this task). This is a real,
 * newly-built aggregation endpoint -- fields below are copied exactly
 * from `CustomerHomeService.get_home`'s return dict, nothing guessed.
 *
 * CONFIRMED GAPS vs. the requested Home design (see delivery report):
 *  - `bookable_categories` carries NO price field (category_id, name,
 *    code, icon_url only) -- "Services near you" pricing has no backend
 *    contract at Home-aggregation level.
 *  - `active_booking` is a SINGLE non-terminal booking summary
 *    (booking_id, booking_number, status, created_at only -- no
 *    technician, ETA, schedule, or rating) -- there is no "recent
 *    bookings" (plural, including completed/cancelled) list in this
 *    payload.
 *  - `campaigns` is ONE generic type -- there is no distinct "offer"
 *    shape (no offer code, no eligibility, no "Apply" state). The
 *    requested "Offers for you" section has no backend contract.
 */
import { z } from "zod";

export const homeAddressDtoSchema = z.object({
  address_id: z.string(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  is_default: z.boolean(),
}).nullable();

export const homeVerticalDtoSchema = z.object({
  vertical_id: z.string(),
  key: z.string(),
  label: z.string(),
  icon: z.string().nullable().optional(),
});

export const homeCategoryDtoSchema = z.object({
  category_id: z.string(),
  name: z.string(),
  // Booking-Assistant Foundation (2026-08-01): backend now forwards the
  // real category `slug` (was silently always-null `code` before this
  // fix) -- required for POST /v1/customer/home-services/booking-drafts,
  // which takes `category_slug`, not an id.
  slug: z.string().nullable().optional(),
  icon_url: z.string().nullable().optional(),
  // Added by the backend (_get_category_meta) so the service card can show
  // the one-line blurb and "Starting at ₹X" the design calls for. Both stay
  // optional/nullable: `starting_price` is null when the catalog carries no
  // configured price for the category at all, and the card then omits the
  // price row rather than rendering ₹0.
  description: z.string().nullable().optional(),
  starting_price: z.number().nullable().optional(),
});

/** A specific problem the customer can tap straight into, skipping the
 * category and issue-picker steps. Carries its own category so the
 * Assistant still receives the full context it needs. */
export const homeQuickIssueDtoSchema = z.object({
  issue_id: z.string(),
  label: z.string(),
  slug: z.string().nullable().optional(),
  category_id: z.string(),
  category_slug: z.string().nullable().optional(),
  category_name: z.string(),
  /** Admin-set artwork for this problem. Null is normal -- the app falls back
   * to a wording-derived glyph rather than showing a blank tile. */
  icon_url: z.string().nullable().optional(),
  /** Dispatch's own urgency grading. Carried but NOT rendered: the customer
   * already knows how bad their problem is, and a red "critical" chip on their
   * own fault would read as alarm rather than information. */
  severity: z.string().nullable().optional(),
  /** "repair" | "consult" | null -- what the customer is trying to do. Null when
   * the wording says neither, in which case the item belongs to no intent
   * section and appears only in the general grids. */
  intent: z.string().nullable().optional(),
});

/** Customer-safe technician identity: name/role/photo only, never a
 * phone number. `rating`/`review_count` come from the real
 * staff_rating_summaries table and are null until that technician has
 * actually been reviewed. */
export const homeTechnicianDtoSchema = z.object({
  name: z.string().nullable().optional(),
  role: z.string().nullable().optional(),
  photo_url: z.string().nullable().optional(),
  rating: z.number().nullable().optional(),
  review_count: z.number().nullable().optional(),
}).nullable();

export const homeActiveBookingDtoSchema = z.object({
  booking_id: z.string(),
  booking_number: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string().nullable().optional(),
  // Added by the backend (customer_home service.py _get_active_booking_summary)
  // specifically so this card could show something meaningful beyond a bare
  // status slug -- this contract previously only declared the 4 fields
  // above, so these were silently dropped even though the API already sent
  // them. All still real booking data, never fabricated: nothing here is a
  // guess at a technician, ETA, or price the backend doesn't have.
  assignment_status: z.string().nullable().optional(),
  issue_summary: z.string().nullable().optional(),
  preferred_date: z.string().nullable().optional(),
  preferred_time_window: z.string().nullable().optional(),
  provider_name: z.string().nullable().optional(),
  // Added for the Home "My Booking" card: the service actually booked,
  // resolved from the catalog by id. `issue_summary` above is the
  // customer's own wording and is not a substitute for it.
  service_name: z.string().nullable().optional(),
  technician: homeTechnicianDtoSchema.optional(),
  // The slot the provider COMMITTED to, off the job. Distinct from the
  // preferred_* fields above, which are only what the customer asked for.
  scheduled_date: z.string().nullable().optional(),
  scheduled_time_window: z.string().nullable().optional(),
  // The provider behind the booking, with the same earned facts and badges the
  // booking-review card shows -- from the same two backend functions, so a
  // provider cannot read one way while being booked and another way once live.
  provider: z.object({
    name: z.string().nullable().optional(),
    verified: z.boolean(),
    rating: z.number().nullable(),
    review_count: z.number(),
    badges: z.array(z.object({
      name: z.string(),
      icon: z.string().nullable().optional(),
      color: z.string().nullable().optional(),
      /** Present only on the provider's STANDING badge (their earned level). The
       * first badge in the list is the standing one when they have a level at all,
       * and it is the single badge compact surfaces show. Absent on the independent
       * badges, which have no level. */
      level: z.number().nullable().optional(),
    }).passthrough()).default([]),
  }).passthrough().nullable().optional(),
});

/** Nullability belongs at the FIELD, not in the shape: baking it into the schema
 * made every element of `active_bookings` nullable as well. */
export const homeActiveBookingDtoNullableSchema = homeActiveBookingDtoSchema.nullable();

export const homeServiceabilityDtoSchema = z.object({
  zipcode: z.string(),
  checked: z.boolean(),
}).nullable();

export const homeCapabilitiesDtoSchema = z.object({
  bargain_available: z.boolean(),
  photo_attach_available: z.boolean(),
  chatbot_language_selectable: z.boolean(),
});

export const customerHomeResponseSchema = z.object({
  response_version: z.number(),
  /** Up to three live bookings, newest first. Empty on an older backend, which
   * the adapter then fills from the single `active_booking` below. */
  active_bookings: z.array(homeActiveBookingDtoSchema).optional().default([]),
  /** The REAL number of live bookings, which can exceed the list above -- it is
   * what decides whether "View all" is offered, so it must not be inferred from
   * the length of a capped list. */
  active_booking_total: z.number().optional(),
  /** Which season the backend ordered this payload for, and how to say so. The
   * app does not compute the season itself: one source of that decision. */
  season: z.string().optional(),
  season_label: z.string().nullable().optional(),
  address: homeAddressDtoSchema,
  serviceability: homeServiceabilityDtoSchema,
  enabled_verticals: z.array(homeVerticalDtoSchema),
  bookable_categories: z.array(homeCategoryDtoSchema),
  quick_issues: z.array(homeQuickIssueDtoSchema).optional().default([]),
  active_booking: homeActiveBookingDtoNullableSchema,
  unread_notification_count: z.number(),
  capabilities: homeCapabilitiesDtoSchema,
});
export type CustomerHomeResponseDto = z.infer<typeof customerHomeResponseSchema>;
