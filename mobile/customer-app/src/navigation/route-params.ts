/**
 * Branded (opaque) identifier types for future route params. These exist so
 * `serviceId: string` and `bookingId: string` cannot be accidentally swapped
 * at a call site — TypeScript alone does not stop that mistake with plain
 * `string`. Runtime values must still be validated (e.g. by a deep-link
 * parser) — a brand only prevents a *compile-time* mix-up, never a runtime one.
 */
export type Brand<T, B extends string> = T & { readonly __brand: B };

export type CategoryId = Brand<string, "CategoryId">;
export type ServiceId = Brand<string, "ServiceId">;
export type BookingDraftId = Brand<string, "BookingDraftId">;
export type AddressId = Brand<string, "AddressId">;
export type BookingId = Brand<string, "BookingId">;
export type ProviderId = Brand<string, "ProviderId">;
export type TechnicianId = Brand<string, "TechnicianId">;
export type NotificationId = Brand<string, "NotificationId">;
export type RewardId = Brand<string, "RewardId">;
export type SupportCaseId = Brand<string, "SupportCaseId">;
export type CampaignCode = Brand<string, "CampaignCode">;
export type ReferralCode = Brand<string, "ReferralCode">;

export type DeepLinkSource = "custom-scheme" | "universal-link" | "app-link" | "notification" | "campaign" | "referral";

/** Where the user should return to after completing a flow entered via deep link/notification. */
export interface EntryContext {
  source: DeepLinkSource;
  returnRouteId?: string;
}
