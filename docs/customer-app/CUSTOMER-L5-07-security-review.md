# CUSTOMER-L5-07 — Security Review

## Ownership Enforcement

- **Address ownership**: `_assert_owns_address` (`serviceability/service.py`)
  enforces `address.customer_id == actor_id` for every read/update/delete
  operation, returning a safe 404 `NotFoundException` rather than a 403
  (avoiding confirming another customer's address exists) — verified by
  reading the actual backend source.
- **Draft ownership**: unchanged from CUSTOMER-L5-06 (`_require_draft`).

## No Sensitive Logging

Verified by grep across `features/address/` and the L5-07-touched parts of
`features/booking-draft/`: every `logger.*` call passes only stable
booleans, enum-like strings (`"permission_denied"`, `"zipcode"`), and
counts — never full address text, never coordinates, never phone/name,
never the free-text `preferred_time_window` value the customer typed.

## Coordinates

`latitude`/`longitude` are only ever populated in local component state
after an explicit, customer-initiated "Use current location" tap, and are
only ever transmitted to the backend as part of the same explicit
`create`/`update` address call the customer confirms by tapping "Save" —
never logged, never included in analytics dimensions, never passed through
a route param (only the resulting `addressId` travels between screens).

## Real, Disclosed Backend Gap: `_resolve_address_snapshot`

`app/engines/home_service_booking/service.py#_resolve_address_snapshot`
performs **no ownership check** on the `address_id` it receives — it loads
`CustomerAddress` by ID and copies its fields into the draft snapshot
without verifying `addr.customer_id == draft.customer_id`. This client
only ever supplies an `address_id` sourced from the customer's own,
already-ownership-filtered `useAddresses()` list — it cannot construct or
guess another customer's address ID through any real UI flow — but the
gap itself is a genuine server-side finding, not something this frontend
sprint can close. Documented here for visibility, consistent with this
project's established pattern of surfacing real backend gaps honestly
rather than silently working around them.

## Isolation Testing

- Address list/create/update/delete/set-default all rely on the backend's
  own `_assert_owns_address` — verified by source reading, not assumed.
- Cross-customer/account-switch isolation: the existing unconditional
  `queryClient.clear()` (CUSTOMER-L5-02) covers the address-list cache;
  no new local persistence was added this sprint that would need its own
  clearing logic (unlike CUSTOMER-L5-06's draft-ID pointer, address data
  has no local-storage footprint at all).

## Input Validation

`address-form-validation.ts` mirrors the real backend's required-field set
exactly (`address_line_1`, `city`, `state`, `zipcode`) — UX-only, since the
backend independently re-validates every field server-side. All text
fields are sanitized (control-character-stripped, whitespace-collapsed,
length-capped) before being held in component state, matching the pattern
established in CUSTOMER-L5-04's search-query normalization.

## No Production Mocks

Grepped `features/address/` for `mock`, `fake`, `TODO`, `FIXME` — none
found. Every address field and serviceability result traces to a real,
schema-validated backend response.

## Location Privacy

- No third-party geocoding provider is used (OS-native geocoder only) —
  no external service receives customer location data at all.
- Location permission is requested only at the point of use, never at
  startup.
- A fully-functional manual-entry path always exists; no screen requires
  location permission to proceed (CUSTOMER-L5-07 §50's "do not trap the
  customer on a permission screen").
