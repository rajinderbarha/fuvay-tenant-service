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
}

/** Deliberately narrow -- only the fields the real Home aggregation
 * endpoint returns (booking_id, booking_number, status, created_at).
 * No technician, ETA, schedule or rating exist in this payload; do not
 * add them to this type without a confirmed backend field. */
export interface HomeActiveBooking {
  bookingId: ServiceBookingId;
  bookingNumber: string | null;
  status: string;
  createdAt: ServerTimestamp | null;
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
  activeBooking: HomeActiveBooking | null;
  unreadNotificationCount: number;
  campaigns: HomeCampaign[];
  capabilities: HomeCapabilities;
}
