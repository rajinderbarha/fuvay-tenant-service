# CUSTOMER-L5-07 — Address Architecture

## Ownership

```
serviceability engine (app/engines/serviceability)
  → canonical CustomerAddress rows — sole source of truth

mobile app
  → no local cache of address content, only React Query's normal
    server-state cache (30s staleTime), never a competing store

booking draft
  → stores a copy (address_id + a denormalized address_snapshot) at the
    moment an address is attached — see draft-architecture.md's existing
    "no competing draft system" principle, extended here: the draft's
    snapshot is a point-in-time copy for display/pricing purposes, not a
    second address record the app maintains
```

## Address Model

Real, complete `CustomerAddress` model
(`app/engines/serviceability/models.py`) — 18 fields, fully mirrored by
`addressSchema` (`domain/address-schema.ts`): `id`, `customer_id`,
`tenant_id`, `name`, `phone`, `address_line_1`, `address_line_2`,
`landmark`, `city`, `district`, `state`, `country`, `zipcode`, `latitude`,
`longitude`, `is_default`, `is_active`, `created_at`, `updated_at`. No
version/revision column exists (consistent with L5-06's draft model — this
backend does not use optimistic concurrency anywhere in this flow).

## Create / Update

Both go straight to the real endpoints
(`POST`/`PUT /v1/customers/me/addresses[/{id}]`). Client-side validation
(`address-form-validation.ts`) exactly mirrors the real backend's own
required-field set (`address_line_1`, `city`, `state`, `zipcode`) — UX
only, since the backend independently re-validates
(`ERR_INVALID_ZIPCODE`/`ERR_INVALID_CITY` on the service layer, plus
Pydantic's own `min_length` constraints). `latitude`/`longitude` are only
ever populated from a customer-confirmed "use current location" action
(`use-current-location.ts`), never silently.

## Delete / Archive

Real soft delete (`DELETE`, sets `is_active=false` server-side). The
backend automatically promotes the next-most-recent address to default if
the deleted one was the default — the client does not need to (and does
not) replicate this logic; it simply refetches the list after deletion.

## Default Address

Real, backend-authoritative (`POST .../set-default`, plus automatic
first-address-becomes-default logic on creation). The client never
maintains a local "this is default" flag independent of what the backend
returns.

## Local Cache

No local persistence of address content at all — only React Query's
standard in-memory cache (`staleTime: 30_000`, scoped by
`(locale, tenant)` defensively, matching every previous sprint's pattern).
Cleared unconditionally on logout via the existing `queryClient.clear()`
call (CUSTOMER-L5-02, unmodified).

## Conflict Handling

Not applicable in the versioned-conflict sense (no version column exists),
matching CUSTOMER-L5-06's draft model. A concurrent edit from another
device would simply last-write-win, consistent with the real backend's own
behavior (`update_address` unconditionally applies non-null fields).

## Draft Attachment

Selecting an address on `AddressListScreen` calls the real draft `PUT`
endpoint with `{address_id}` — the backend's own `_resolve_address_snapshot`
then copies the address's display fields into
`draft.address_snapshot`/`draft.city`/`draft.zipcode` server-side (see
contract-matrix.md). **A real, disclosed backend gap**:
`_resolve_address_snapshot` performs no ownership check on the supplied
`address_id` — this client only ever passes an ID sourced from the
customer's own `useAddresses()` list, never an arbitrary one, but the gap
itself is not fixable from this frontend sprint (see security-review.md).

## Isolation

Every address endpoint enforces `customer_id` ownership server-side
(`_assert_owns_address`, 404 `NotFoundException` on mismatch — a safe
not-found response rather than a 403 that would confirm the address
exists for someone else). The client adds no isolation logic of its own
beyond the standard locale/tenant-scoped query key and the unconditional
`queryClient.clear()` on logout already established in CUSTOMER-L5-02.
