/**
 * Centralized, typed route identifiers. Future sprints add screens under
 * these names instead of scattering string literals across the codebase.
 * Only `DesignSystemShowcase` (dev-only) is actually wired to a screen in
 * this sprint — the rest are reserved names for future sprints' navigators.
 */
export const ROUTE_NAMES = {
  startup: "Startup",
  startupError: "StartupError",
  offlineStartup: "OfflineStartup",
  maintenance: "Maintenance",
  mandatoryUpdate: "MandatoryUpdate",
  unsupportedBuild: "UnsupportedBuild",
  appUnavailable: "AppUnavailable",
  baselineLanding: "BaselineLanding",
  authentication: "Authentication",
  home: "Home",
  categoryDetail: "CategoryDetail",
  search: "Search",
  serviceDetails: "ServiceDetails",
  bookingAssistant: "BookingAssistant",
  bookingDraft: "BookingDraft",
  bookingMedia: "BookingMedia",
  addressSelection: "AddressSelection",
  addressForm: "AddressForm",
  serviceabilityCheck: "ServiceabilityCheck",
  providerPreview: "ProviderPreview",
  pricing: "Pricing",
  bargain: "Bargain",
  bookingReview: "BookingReview",
  bookingSuccess: "BookingSuccess",
  bookingsList: "BookingsList",
  bookingDetail: "BookingDetail",
  tracking: "Tracking",
  quoteDecision: "QuoteDecision",
  notifications: "Notifications",
  rewards: "Rewards",
  profile: "Profile",
  sessions: "Sessions",
  support: "Support",
  legalTerms: "LegalTerms",
  legalPrivacy: "LegalPrivacy",
  designSystemShowcase: "DesignSystemShowcase",
} as const;

export type RouteName = (typeof ROUTE_NAMES)[keyof typeof ROUTE_NAMES];
