import { AddressId, CategoryId, ServiceBookingId, VerticalId } from "./ids";
import { VerticalKey } from "./catalog";
import { ServerTimestamp } from "./dates";
import { ProviderBadge } from "./providerBadges";

export interface HomeAddressSummary {
  addressId: AddressId;
  city: string | null;
  zipcode: string | null;
  isDefault: boolean;
}

export interface HomeVertical {
  verticalId: VerticalId;
  key: VerticalKey | string;
  label: string;
  icon: string | null;
}

export interface HomeCategory {
  categoryId: CategoryId;
  name: string;
  /** Required to start a booking draft (`category_slug`). Null only if
   * the backend's own catalog row genuinely has no slug -- such a
   * category cannot be tapped into the Assistant (see HomeServiceCard). */
  slug: string | null;
  iconUrl: string | null;
  /** One-line blurb under the name on the service card. Straight from the
   * catalog row; null when the admin never wrote one. */
  description: string | null;
  /** Lowest genuinely-configured price across this category's active
   * services (see CustomerHomeService._get_category_meta). Null when the
   * catalog carries no price at all -- the card then omits the price row
   * rather than showing a fabricated or ₹0 figure. */
  startingPrice: number | null;
}

/** A named problem ("AC Not Cooling", "Drain Blocked") the customer can
 * tap to jump straight into the Assistant with both the category and the
 * issue already chosen, skipping the category and issue-picker steps.
 *
 * Deliberately carries no price. The backend links each issue to a priced
 * service, but the final figure depends on answers the Assistant has not
 * asked yet, so a number here would be a quote the booking flow might not
 * honour. */
export interface HomeQuickIssue {
  issueId: string;
  label: string;
  categoryId: CategoryId;
  /** Null blocks the tap: the Assistant is entered by category slug. */
  categorySlug: string | null;
  categoryName: string;
  /** Admin-set artwork. Null falls back to a wording-derived glyph. */
  iconUrl: string | null;
  /** What the customer is trying to do: fix a fault, or get something scoped and
   * quoted. Null when the wording says neither -- such an item is shown in the
   * general grids and in no intent section, rather than forced into one. */
  intent: HomeProblemIntent;
}

export type HomeProblemIntent = "repair" | "consult" | null;

/** Only fields the real Home aggregation endpoint returns. Extended
 * 2026-08 to include issue_summary/provider_name/preferred_date/
 * preferred_time_window/assignment_status, which the backend
 * (customer_home service.py) already sends -- there is still no
 * technician identity, live ETA, or rating in this payload; do not add
 * those without a confirmed backend field. */
/** Name/role/photo only -- never a phone number. `rating` is null until
 * the technician has actually been reviewed; it is never defaulted to a
 * flattering number, so the card simply omits the star. */
export interface HomeTechnician {
  name: string | null;
  role: string | null;
  photoUrl: string | null;
  rating: number | null;
  reviewCount: number | null;
}

export interface HomeActiveBooking {
  bookingId: ServiceBookingId;
  bookingNumber: string | null;
  status: string;
  createdAt: ServerTimestamp | null;
  assignmentStatus: string | null;
  issueSummary: string | null;
  /** The service actually booked, from the catalog. Distinct from
   * `issueSummary`, which is the customer's own description. */
  serviceName: string | null;
  preferredDate: string | null;
  preferredTimeWindow: string | null;
  providerName: string | null;
  /** The slot the provider committed to. Null until one is scheduled --
   * distinct from `preferredDate`/`preferredTimeWindow`, which are only what
   * the customer asked for and must never be shown as an appointment. */
  scheduledDate: string | null;
  scheduledTimeWindow: string | null;
  /** The provider behind the booking. Same earned facts and badges as the
   * booking-review card, from the same backend functions. */
  provider: HomeBookingProvider | null;
  /** Null until a technician is assigned to this booking's job. */
  technician: HomeTechnician | null;
}

export interface HomeBookingProvider {
  name: string | null;
  verified: boolean;
  rating: number | null;
  reviewCount: number;
  /** Backend-authored trust chips. Empty is a valid, honest state. */
  /** Earned badges, standing FIRST when the provider has a level. `level` is set
   * only on that standing badge -- see providerBadges.standingBadge. */
  badges: ProviderBadge[];
}

export interface HomeServiceability {
  zipcode: string;
  checked: boolean;
}

export interface HomeCapabilities {
  bargainAvailable: boolean;
  photoAttachAvailable: boolean;
  chatbotLanguageSelectable: boolean;
}

export interface CustomerHome {
  responseVersion: number;
  address: HomeAddressSummary | null;
  serviceability: HomeServiceability | null;
  enabledVerticals: HomeVertical[];
  bookableCategories: HomeCategory[];
  quickIssues: HomeQuickIssue[];
  /** Up to three live bookings, newest first. */
  activeBookings: HomeActiveBooking[];
  /** How many live bookings there really are -- can exceed `activeBookings`. */
  activeBookingTotal: number;
  /** The newest one. Always `activeBookings[0]`, kept for callers that only ever
   * needed the one. */
  activeBooking: HomeActiveBooking | null;
  unreadNotificationCount: number;
  /** The season the backend ordered this payload for ("monsoon"), and the
   * customer-facing way to say it ("Monsoon picks"). Null on an older backend,
   * in which case the app shows no seasonal wording rather than guessing. */
  season: string | null;
  seasonLabel: string | null;
  capabilities: HomeCapabilities;
}
