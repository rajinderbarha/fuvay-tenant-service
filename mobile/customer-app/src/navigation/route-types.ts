import type { ROUTE_NAMES } from "./route-names";
import type { CategoryId, ServiceId, BookingDraftId, AddressId, BookingId, EntryContext } from "./route-params";

/**
 * Typed param lists per route. Only the routes actually reachable this
 * sprint have concrete (empty/system) param types; the rest are placeholders
 * for later sprints to fill in as the real screens are built, so future
 * navigators can import from one typed source instead of `any`. Branded ID
 * types (route-params.ts) are used where a later sprint's route accepts an
 * identifier, so a service ID can never be passed where a booking ID is
 * expected without a compile error.
 */
export type RootStackParamList = {
  [ROUTE_NAMES.startup]: undefined;
  [ROUTE_NAMES.startupError]: { errorReferenceId: string };
  [ROUTE_NAMES.offlineStartup]: undefined;
  [ROUTE_NAMES.maintenance]: undefined;
  [ROUTE_NAMES.mandatoryUpdate]: undefined;
  [ROUTE_NAMES.unsupportedBuild]: undefined;
  [ROUTE_NAMES.appUnavailable]: { reasonKey: string };
  [ROUTE_NAMES.baselineLanding]: undefined;
  [ROUTE_NAMES.authentication]: { entryContext?: EntryContext } | undefined;
  [ROUTE_NAMES.home]: undefined;
  [ROUTE_NAMES.categoryDetail]: { categoryId: CategoryId };
  [ROUTE_NAMES.search]: { initialQuery?: string } | undefined;
  [ROUTE_NAMES.serviceDetails]: { serviceId: ServiceId; categoryId: CategoryId };
  [ROUTE_NAMES.bookingAssistant]: { serviceId: ServiceId; categoryId: CategoryId } | undefined;
  [ROUTE_NAMES.bookingDraft]: { serviceId: ServiceId; categoryId: CategoryId; brandId?: string; offeringTypeId?: string; issueSummary?: string };
  [ROUTE_NAMES.bookingMedia]: { draftId: BookingDraftId };
  [ROUTE_NAMES.addressSelection]: { draftId: BookingDraftId };
  [ROUTE_NAMES.addressForm]: { draftId: BookingDraftId; addressId?: AddressId };
  [ROUTE_NAMES.serviceabilityCheck]: { draftId: BookingDraftId; addressId: AddressId };
  /**
   * The real backend has no provider-preview-by-ID lookup — matching is
   * always performed against a draft (`POST /{draftId}/match-and-price`),
   * which auto-selects one provider server-side. `providerId` was this
   * route's originally-reserved (unbuilt) param shape; CUSTOMER-L5-08
   * replaces it with the real shape this screen actually needs.
   */
  [ROUTE_NAMES.providerPreview]: { draftId: BookingDraftId };
  [ROUTE_NAMES.pricing]: { bookingDraftId: BookingDraftId };
  [ROUTE_NAMES.bargain]: { bookingDraftId: BookingDraftId };
  [ROUTE_NAMES.bookingReview]: { bookingDraftId: BookingDraftId };
  [ROUTE_NAMES.bookingSuccess]: { bookingId: BookingId };
  [ROUTE_NAMES.bookingsList]: undefined;
  [ROUTE_NAMES.bookingDetail]: { bookingId: BookingId };
  [ROUTE_NAMES.tracking]: { bookingId: BookingId };
  [ROUTE_NAMES.quoteDecision]: { bookingId: BookingId };
  [ROUTE_NAMES.notifications]: undefined;
  [ROUTE_NAMES.rewards]: undefined;
  [ROUTE_NAMES.profile]: undefined;
  [ROUTE_NAMES.sessions]: undefined;
  [ROUTE_NAMES.support]: undefined;
  [ROUTE_NAMES.legalTerms]: undefined;
  [ROUTE_NAMES.legalPrivacy]: undefined;
  [ROUTE_NAMES.designSystemShowcase]: undefined;
};
