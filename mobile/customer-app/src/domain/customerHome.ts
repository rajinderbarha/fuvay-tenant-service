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

export interface HomeServiceGroup {
  serviceGroupId: string;
  name: string;
  slug: string;
  description: string | null;
  iconUrl: string | null;
  categoryId: CategoryId;
  categorySlug: string;
}

/** Concrete customer work authored in Admin > Master Services and published
 * by at least one eligible provider at the selected ZIP. */
export interface HomeMasterService {
  masterServiceId: string;
  name: string;
  slug: string;
  description: string | null;
  iconUrl: string | null;
  serviceGroupId: string;
  serviceGroupName: string;
  serviceGroupSlug: string;
  categoryId: CategoryId;
  categorySlug: string;
}

export interface HomeCampaign {
  campaignId: string;
  placement: string;
  variant: string;
  themeKey: string;
  sectionTitle: string | null;
  priority: number;
  sponsored: boolean;
  badge: string;
  title: string;
  subtitle: string;
  offerText: string | null;
  imageUrl: string;
  actionLabel: string;
  actionUrl: string | null;
  categorySlug: string | null;
  serviceGroupSlug: string | null;
  startsAt: string | null;
  endsAt: string | null;
}

export interface HomeSectionConfig {
  key: string;
  enabled: boolean;
  title: string | null;
  variant: string;
  maxItems: number;
  spacing: "compact" | "standard" | "generous";
  surface: "canvas" | "subtle" | "raised" | "brand_tint";
}

export const DEFAULT_HOME_SECTIONS: HomeSectionConfig[] = [
  ["hero", null, "marketplace", 5, true, "compact", "canvas"],
  ["service_groups", "Popular services", "compact_grid", 8, true, "compact", "canvas"],
  ["recent_bookings", "Recent bookings", "compact_rail", 3, true, "compact", "canvas"],
  ["featured_services", "Featured services", "compact_cards", 6, true, "compact", "canvas"],
  ["master_services", "Recommended for you", "recommendation_cards", 8, true, "compact", "canvas"],
  ["banners", null, "contained", 4, true, "standard", "canvas"],
  ["collection", "Offers for you", "editorial_cards", 8, true, "compact", "canvas"],
  ["spotlight", "In the spotlight", "cinematic_card", 2, true, "compact", "canvas"],
  ["global_services", "Web & mobile development", "compact_services", 6, true, "compact", "canvas"],
  ["trust_strip", null, "icon_row", 4, true, "compact", "subtle"],
  ["live_booking", "Your live booking", "timeline", 1, false, "compact", "canvas"],
  ["stories", "Ideas and offers", "landscape", 8],
  ["mosaic", "Fresh ways to care for home", "asymmetric", 3],
  ["assistant", null, "command_strip", 1],
  ["featured_problems", "What needs fixing?", "editorial_list", 8],
  ["active_bookings", "More active bookings", "stack", 3],
  ["repair_problems", "Repairs you can book now", "editorial_rail", 12],
  ["consultation_problems", "Get an expert opinion", "editorial_list", 8],
  ["more_problems", "More ways we can help", "compact_grid", 12],
  ["notices", null, "strips", 2],
  ["support_actions", null, "utility_rows", 2],
].map(([key, title, variant, maxItems, enabled, spacing, surface]) => ({
  key: String(key),
  enabled: enabled == null ? ["hero", "service_groups", "recent_bookings", "featured_services", "master_services", "banners", "collection", "spotlight", "global_services", "trust_strip"].includes(String(key)) : Boolean(enabled),
  title: title == null ? null : String(title),
  variant: String(variant),
  maxItems: Number(maxItems),
  spacing: (spacing ?? "standard") as HomeSectionConfig["spacing"],
  surface: (surface ?? "canvas") as HomeSectionConfig["surface"],
}));

export interface CustomerHome {
  responseVersion: number;
  address: HomeAddressSummary | null;
  serviceability: HomeServiceability | null;
  enabledVerticals: HomeVertical[];
  bookableCategories: HomeCategory[];
  bookableServiceGroups: HomeServiceGroup[];
  bookableMasterServices: HomeMasterService[];
  quickIssues: HomeQuickIssue[];
  /** Content for fixed product-owned placements. Admin controls content and
   * targeting, never native section order or component types. */
  campaigns: HomeCampaign[];
  /** Ordered, admin-published list of native component slots. Only known
   * app-owned section keys render; unknown future keys are ignored safely. */
  sections: HomeSectionConfig[];
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
