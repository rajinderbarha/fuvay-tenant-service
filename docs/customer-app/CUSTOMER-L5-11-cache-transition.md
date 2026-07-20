# CUSTOMER-L5-11 — Cache Transition

## No Dedicated Query Key for Review/Confirmation Mutations

`useBookingReview` and `useConfirmBooking` are both `useMutation`s
(mirroring every prior sprint's identical pattern for `POST`-only,
no-independent-GET real endpoints) — their results live only in the
mutation's own in-memory state, composed by `useBookingReviewFlow`/
`useConfirmBookingFlow` into the two pure state machines
(`booking-state-machine.md`).

## A Real `useQuery` for the Canonical Booking

`useBookingDetail` (`GET /bookings/{id}`) is this sprint's one genuine
cacheable read — `bookingQueryKeys.detail(bookingId, locale, tenantId)`,
following the exact same locale/tenant-scoping convention every prior
sprint's query keys use (`draftQueryKeys`, unchanged since
CUSTOMER-L5-06).

## Draft Invalidation After Confirmation

`useInvalidateDraftAfterBooking()` invalidates the existing
`["bookingDraft", "detail", draftId, locale, tenantId]` cache entry
(the exact key `draftQueryKeys.detail` produces, referenced directly by
its literal array shape to avoid a new cross-feature import cycle)
immediately after a `confirmed` result — called from
`BookingReviewScreen`'s confirmation effect. This prevents any other
still-mounted screen from showing a stale, pre-confirmation snapshot of a
draft that has since become terminal (`"confirmed"`).

## No Global Cache Clear

Per §39's explicit instruction, this sprint invalidates only the specific
draft-detail entry — it does not call a blanket `queryClient.clear()` or
`invalidateQueries()` with no key filter. The public catalogue cache,
customer profile, and any other unrelated cached data are left untouched.

## Pricing/Bargain/Match State

No explicit clearing of `features/pricing/`'s or `features/bargain/`'s
mutation state is needed — both are `useMutation`s whose state lives
entirely within their own screens' component trees, unmounted (and thus
naturally discarded) the moment `navigation.reset()` removes those
screens from the stack (`booking-creation-architecture.md`'s Navigation
Reset section). There is no separate, longer-lived cache entry for either
that would otherwise need explicit invalidation.

## Logout / Account Switch

No new local persistence was added this sprint beyond the standard
`useQuery` cache entry for booking detail, which is discarded by the
existing unconditional `queryClient.clear()` (CUSTOMER-L5-02 pattern) on
logout/account-switch — unchanged, no additional clearing logic required.

## Booking Cache Initialization

Per §39's "add canonical booking to booking cache," `useBookingDetail`'s
own `useQuery` call on `BookingConfirmationScreen`'s mount is itself the
initialization — React Query populates the cache entry as a natural side
effect of the first successful fetch; no separate manual
`queryClient.setQueryData` call was needed (unlike L5-08/09/10's mutation
`onSuccess` patches, which exist specifically because those are
mutations without their own query to populate).
