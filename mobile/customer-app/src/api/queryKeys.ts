/**
 * Typed query-key factory. Every server-state read this app performs goes
 * through one of these functions so two features can never collide on a
 * cache entry by writing similar-looking key arrays independently. Keys
 * always include every identifier/filter that materially changes the
 * result, and NEVER include a token or other sensitive value.
 */
import {
  AddressId, BookingDraftId, ServiceBookingId, ServiceJobId, QuoteId,
  ConversationId, CategoryId, CustomerId,
} from "../domain/ids";

export const queryKeys = {
  customerProfile: () => ["customer", "profile"] as const,

  /** ZIP is part of the key's identity (Level 5 Home spec: "Address/ZIP
   * included in query identity") -- `undefined` (no override) is its own
   * distinct cache entry from any specific ZIP string. */
  home: {
    aggregate: (zipcode?: string) => ["home", "aggregate", zipcode ?? null] as const,
  },

  verticals: () => ["verticals", "enabled"] as const,

  catalog: {
    categories: () => ["catalog", "categories"] as const,
    category: (slug: string) => ["catalog", "categories", slug] as const,
    offerings: (categorySlug: string) => ["catalog", "categories", categorySlug, "offerings"] as const,
    offering: (categorySlug: string, offeringSlug: string) =>
      ["catalog", "categories", categorySlug, "offerings", offeringSlug] as const,
  },

  serviceability: {
    check: (zipcode: string, categoryId?: CategoryId) =>
      ["serviceability", zipcode, categoryId ?? null] as const,
  },

  addresses: {
    list: (customerId: CustomerId) => ["addresses", customerId] as const,
    detail: (addressId: AddressId) => ["addresses", "detail", addressId] as const,
  },

  bookingDrafts: {
    detail: (draftId: BookingDraftId) => ["bookingDrafts", draftId] as const,
  },

  bookings: {
    list: (filters: { status?: string; page?: number } = {}) =>
      ["bookings", "list", filters.status ?? "all", filters.page ?? 1] as const,
    detail: (bookingId: ServiceBookingId) => ["bookings", "detail", bookingId] as const,
    tracking: (bookingId: ServiceBookingId) => ["bookings", "tracking", bookingId] as const,
  },

  serviceJobs: {
    detail: (jobId: ServiceJobId) => ["serviceJobs", "detail", jobId] as const,
    tracking: (jobId: ServiceJobId) => ["serviceJobs", "tracking", jobId] as const,
    checklist: (jobId: ServiceJobId) => ["serviceJobs", "checklist", jobId] as const,
  },

  quotes: {
    forJob: (jobId: ServiceJobId) => ["quotes", "forJob", jobId] as const,
    detail: (quoteId: QuoteId) => ["quotes", "detail", quoteId] as const,
    events: (quoteId: QuoteId) => ["quotes", "events", quoteId] as const,
  },

  reviews: {
    eligibility: (jobId: ServiceJobId) => ["reviews", "eligibility", jobId] as const,
    mine: (filters: { page?: number } = {}) => ["reviews", "mine", filters.page ?? 1] as const,
  },

  conversations: {
    list: () => ["conversations", "list"] as const,
    detail: (conversationId: ConversationId) => ["conversations", "detail", conversationId] as const,
    messages: (conversationId: ConversationId, page: number = 1) =>
      ["conversations", "detail", conversationId, "messages", page] as const,
  },

  notifications: {
    list: (filter: "all" | "unread") => ["notifications", "list", filter] as const,
    unreadCount: () => ["notifications", "unreadCount"] as const,
  },
} as const;
