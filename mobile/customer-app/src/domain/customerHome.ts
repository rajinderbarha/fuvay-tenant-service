import { AddressId, CategoryId, ServiceBookingId, VerticalId } from "./ids";
import { VerticalKey } from "./catalog";
import { ServerTimestamp } from "./dates";

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
}

/** Only fields the real Home aggregation endpoint returns. Extended
 * 2026-08 to include issue_summary/provider_name/preferred_date/
 * preferred_time_window/assignment_status, which the backend
 * (customer_home service.py) already sends -- there is still no
 * technician identity, live ETA, or rating in this payload; do not add
 * those without a confirmed backend field. */
export interface HomeActiveBooking {
  bookingId: ServiceBookingId;
  bookingNumber: string | null;
  status: string;
  createdAt: ServerTimestamp | null;
  assignmentStatus: string | null;
  issueSummary: string | null;
  preferredDate: string | null;
  preferredTimeWindow: string | null;
  providerName: string | null;
}

export interface HomeServiceability {
  zipcode: string;
  checked: boolean;
}

export interface HomeCampaign {
  campaignId: string;
  eyebrow: string | null;
  title: string;
  description: string | null;
  artworkUrlLight: string | null;
  artworkUrlDark: string | null;
  ctaLabel: string | null;
  ctaDeeplink: string | null;
  priority: number;
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
  activeBooking: HomeActiveBooking | null;
  unreadNotificationCount: number;
  campaigns: HomeCampaign[];
  capabilities: HomeCapabilities;
}
