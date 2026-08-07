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
}).nullable();

export const homeServiceabilityDtoSchema = z.object({
  zipcode: z.string(),
  checked: z.boolean(),
}).nullable();

export const homeCampaignDtoSchema = z.object({
  campaign_id: z.string(),
  eyebrow: z.string().nullable().optional(),
  title: z.string(),
  description: z.string().nullable().optional(),
  artwork_url_light: z.string().nullable().optional(),
  artwork_url_dark: z.string().nullable().optional(),
  cta_label: z.string().nullable().optional(),
  cta_deeplink: z.string().nullable().optional(),
  priority: z.number(),
});

export const homeCapabilitiesDtoSchema = z.object({
  bargain_available: z.boolean(),
  photo_attach_available: z.boolean(),
  chatbot_language_selectable: z.boolean(),
});

export const customerHomeResponseSchema = z.object({
  response_version: z.number(),
  address: homeAddressDtoSchema,
  serviceability: homeServiceabilityDtoSchema,
  enabled_verticals: z.array(homeVerticalDtoSchema),
  bookable_categories: z.array(homeCategoryDtoSchema),
  active_booking: homeActiveBookingDtoSchema,
  unread_notification_count: z.number(),
  campaigns: z.array(homeCampaignDtoSchema),
  capabilities: homeCapabilitiesDtoSchema,
});
export type CustomerHomeResponseDto = z.infer<typeof customerHomeResponseSchema>;
