/**
 * Branded identifier types. Every ID a customer-app module handles is a
 * distinct nominal type, so `bookingId` can never be passed where a
 * `jobId` is expected even though both are plain strings/UUIDs at
 * runtime. Backend-owned identifiers (UUIDs, ULIDs, slugs) are NEVER
 * coerced to number -- they are opaque strings end to end.
 */
declare const brand: unique symbol;
export type Branded<T, B extends string> = T & { readonly [brand]: B };

function makeId<B extends string>(_b: B) {
  return (value: string) => value as Branded<string, B>;
}

export type CustomerId = Branded<string, "CustomerId">;
export type TenantId = Branded<string, "TenantId">;
export type VerticalId = Branded<string, "VerticalId">;
export type CategoryId = Branded<string, "CategoryId">;
export type ServiceGroupId = Branded<string, "ServiceGroupId">;
export type MasterServiceId = Branded<string, "MasterServiceId">;
export type JobTypeId = Branded<string, "JobTypeId">;
export type ServiceTypeId = Branded<string, "ServiceTypeId">;
export type BrandId = Branded<string, "BrandId">;
export type BookingDraftId = Branded<string, "BookingDraftId">;
export type ServiceBookingId = Branded<string, "ServiceBookingId">;
export type ServiceJobId = Branded<string, "ServiceJobId">;
export type QuoteId = Branded<string, "QuoteId">;
export type BargainSessionId = Branded<string, "BargainSessionId">;
export type AddressId = Branded<string, "AddressId">;
export type ConversationId = Branded<string, "ConversationId">;
export type NotificationId = Branded<string, "NotificationId">;
export type ReviewId = Branded<string, "ReviewId">;
export type InvoiceId = Branded<string, "InvoiceId">;
export type ComplaintId = Branded<string, "ComplaintId">;
export type DirectPaymentId = Branded<string, "DirectPaymentId">;
export type IdempotencyKey = Branded<string, "IdempotencyKey">;

export const asCustomerId = makeId("CustomerId");
export const asTenantId = makeId("TenantId");
export const asVerticalId = makeId("VerticalId");
export const asCategoryId = makeId("CategoryId");
export const asServiceGroupId = makeId("ServiceGroupId");
export const asMasterServiceId = makeId("MasterServiceId");
export const asJobTypeId = makeId("JobTypeId");
export const asServiceTypeId = makeId("ServiceTypeId");
export const asBrandId = makeId("BrandId");
export const asBookingDraftId = makeId("BookingDraftId");
export const asServiceBookingId = makeId("ServiceBookingId");
export const asServiceJobId = makeId("ServiceJobId");
export const asQuoteId = makeId("QuoteId");
export const asBargainSessionId = makeId("BargainSessionId");
export const asAddressId = makeId("AddressId");
export const asConversationId = makeId("ConversationId");
export const asNotificationId = makeId("NotificationId");
export const asReviewId = makeId("ReviewId");
export const asInvoiceId = makeId("InvoiceId");
export const asComplaintId = makeId("ComplaintId");
export const asDirectPaymentId = makeId("DirectPaymentId");
export const asIdempotencyKey = makeId("IdempotencyKey");
