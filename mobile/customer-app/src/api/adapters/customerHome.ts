import { CustomerHomeResponseDto, customerHomeResponseSchema } from "../contracts/customerHome";
import { CustomerHome } from "../../domain/customerHome";
import { asAddressId, asCategoryId, asServiceBookingId, asVerticalId } from "../../domain/ids";
import { parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError } from "../../domain/errors";

export function parseCustomerHomeDto(raw: unknown): CustomerHomeResponseDto {
  const result = customerHomeResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("CustomerHomeResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/** No status/enum validation against domain/status.ts here on purpose --
 * `active_booking.status` uses the ServiceBooking status vocabulary
 * already validated by the dedicated bookings adapter (api/adapters/
 * booking.ts) when that record is fetched in full; this aggregation
 * summary only needs a display-safe string, so an unrecognized value is
 * shown as-is rather than throwing and breaking the whole Home screen
 * over one unfamiliar status on a secondary field. */
export function adaptCustomerHome(dto: CustomerHomeResponseDto): CustomerHome {
  return {
    responseVersion: dto.response_version,
    address: dto.address
      ? { addressId: asAddressId(dto.address.address_id), city: dto.address.city, zipcode: dto.address.zipcode, isDefault: dto.address.is_default }
      : null,
    serviceability: dto.serviceability ? { zipcode: dto.serviceability.zipcode, checked: dto.serviceability.checked } : null,
    enabledVerticals: dto.enabled_verticals.map(v => ({
      verticalId: asVerticalId(v.vertical_id), key: v.key, label: v.label, icon: v.icon ?? null,
    })),
    bookableCategories: dto.bookable_categories.map(c => ({
      categoryId: asCategoryId(c.category_id), name: c.name, slug: c.slug ?? null, iconUrl: c.icon_url ?? null,
      description: c.description ?? null, startingPrice: c.starting_price ?? null,
    })),
    quickIssues: dto.quick_issues.map(i => ({
      issueId: i.issue_id,
      label: i.label,
      categoryId: asCategoryId(i.category_id),
      categorySlug: i.category_slug ?? null,
      categoryName: i.category_name,
    })),
    activeBooking: dto.active_booking
      ? {
          bookingId: asServiceBookingId(dto.active_booking.booking_id),
          bookingNumber: dto.active_booking.booking_number ?? null,
          status: dto.active_booking.status,
          createdAt: dto.active_booking.created_at ? parseServerTimestamp(dto.active_booking.created_at, "active_booking.created_at") : null,
          assignmentStatus: dto.active_booking.assignment_status ?? null,
          issueSummary: dto.active_booking.issue_summary ?? null,
          preferredDate: dto.active_booking.preferred_date ?? null,
          preferredTimeWindow: dto.active_booking.preferred_time_window ?? null,
          providerName: dto.active_booking.provider_name ?? null,
          serviceName: dto.active_booking.service_name ?? null,
          technician: dto.active_booking.technician
            ? {
                name: dto.active_booking.technician.name ?? null,
                role: dto.active_booking.technician.role ?? null,
                photoUrl: dto.active_booking.technician.photo_url ?? null,
                rating: dto.active_booking.technician.rating ?? null,
                reviewCount: dto.active_booking.technician.review_count ?? null,
              }
            : null,
        }
      : null,
    unreadNotificationCount: dto.unread_notification_count,
    campaigns: dto.campaigns
      .map(c => ({
        campaignId: c.campaign_id,
        eyebrow: c.eyebrow ?? null,
        title: c.title,
        description: c.description ?? null,
        artworkUrlLight: c.artwork_url_light ?? null,
        artworkUrlDark: c.artwork_url_dark ?? null,
        ctaLabel: c.cta_label ?? null,
        ctaDeeplink: c.cta_deeplink ?? null,
        priority: c.priority,
      }))
      .sort((a, b) => a.priority - b.priority),
    capabilities: {
      bargainAvailable: dto.capabilities.bargain_available,
      photoAttachAvailable: dto.capabilities.photo_attach_available,
      chatbotLanguageSelectable: dto.capabilities.chatbot_language_selectable,
    },
  };
}
