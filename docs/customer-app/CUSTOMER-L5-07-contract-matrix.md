# CUSTOMER-L5-07 — Contract Matrix

Verified by direct reading of `app/engines/serviceability/router.py`,
`service.py`, `models.py`, `schemas.py`, and
`app/engines/home_service_booking/service.py`,
`serviceability_service.py`, `constants.py` — cross-checked by an
independent research pass reaching identical conclusions on every point.

## Address

| Concept | Backend contract | Auth | Client type | API method | Query/mutation | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| List addresses | `GET /v1/customers/me/addresses` | Required | `ValidatedAddress[]` | `addressApi.listAddresses` | `useAddresses` | `AddressListScreen` | `address-schema.test.ts` | MATCHED |
| Create address | `POST /v1/customers/me/addresses` | Required | same | `addressApi.createAddress` | `useCreateAddress` | `AddressFormScreen` | same | MATCHED |
| Get address | `GET /v1/customers/me/addresses/{id}` | Required, ownership-enforced (404 on mismatch) | same | `addressApi.getAddress` | `useAddress` | `AddressFormScreen` (edit mode) | same | MATCHED |
| Update address | `PUT /v1/customers/me/addresses/{id}` | Required, ownership-enforced | same | `addressApi.updateAddress` | `useUpdateAddress` | `AddressFormScreen` | same | MATCHED |
| Delete address | `DELETE /v1/customers/me/addresses/{id}` (soft) | Required, ownership-enforced | `{address_id, deleted}` | `addressApi.deleteAddress` | `useDeleteAddress` | `AddressListScreen` | same | MATCHED |
| Set default | `POST /v1/customers/me/addresses/{id}/set-default` | Required, ownership-enforced | `ValidatedAddress` | `addressApi.setDefaultAddress` | `useSetDefaultAddress` | `AddressListScreen` | same | MATCHED |
| Address version/revision | No column exists | — | — | — | — | No conflict-detection UI | — | MISSING_BACKEND |
| Address-ownership check when attaching to a draft | `_resolve_address_snapshot` (home_service_booking) performs **no ownership check** at all — copies any `address_id`'s fields regardless of the requesting customer | — | — | Client only ever passes an `address_id` obtained from the customer's own `useAddresses` list, never an arbitrary one | — | — | — | MISMATCHED — real backend gap, not fixable client-side (see security-review.md) |

## Location

| Concept | Backend contract | Client implementation | Status |
|---|---|---|---|
| Current-device coordinates | N/A — device capability, not a backend endpoint | `expo-location#getCurrentPositionAsync`, permission via `requestForegroundPermissionsAsync` | MATCHED (real device capability, first use in this app) |
| Reverse geocoding (coordinates → address fields) | **Does not exist anywhere in the backend** — confirmed by exhaustive grep | `expo-location#reverseGeocodeAsync` — OS-level (iOS/Android native geocoder), no third-party API key, no backend call | MISSING_BACKEND (real client-only substitute, clearly documented as such, always customer-editable before save — never auto-submitted) |
| Forward geocoding (address text → coordinates) | Does not exist | Not implemented — no product need identified without a backend consumer for the resulting coordinates | NOT_APPLICABLE |
| Structured city/state/district picker (`location_engine`'s public cascading endpoints) | Real: `GET /v1/public/locations/states\|districts\|cities\|zones` (no auth) | **Not used this sprint** — see known-gaps.md; manual free-text entry (matching the real `AddressCreate` schema's own field types) is used instead, to keep this sprint's scope bounded | NOT_APPLICABLE (real, deliberately deferred) |

## Serviceability

| Concept | Backend contract | Auth | Client type | API method | Query/mutation | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Draft serviceability check | `POST /v1/customer/home-services/booking-drafts/{id}/serviceability-check` — internally `HomeServiceServiceabilityService.check(category_id, offering_id, city, zipcode)` | Required, ownership-enforced via `_require_draft` | `ValidatedServiceabilityResult` | `draftApi.checkServiceability` | `useCheckServiceability` | `ServiceabilityScreen` | `serviceability-schema.test.ts` | MATCHED |
| Serviceable result | `{serviceable: true, available_provider_count, matched_by: "zipcode"\|"city", message, reason_code: null}` | — | — | — | — | Shown as a real success state with the real `message` | tested | MATCHED |
| Not-serviceable result | `{serviceable: false, available_provider_count: 0, matched_by: null, message, reason_code: "NO_PROVIDER_IN_ZIPCODE"\|"NO_PROVIDER_IN_CITY"\|"HOME_BOOKING_CATEGORY_INVALID"\|"HOME_BOOKING_OFFERING_INVALID"}` | — | — | — | — | Shown as a real, honest unavailable state with the real `message`; category/offering-invalid reasons additionally suggest returning to the service | tested | MATCHED |
| General serviceability engine (`/v1/serviceability/*`) | Real, but keyed to a third, unrelated catalog (`ServiceCatalogItem`) never used by the booking-draft flow | — | — | Not used | — | — | — | NOT_APPLICABLE (real, deliberately not adopted — see baseline-verification.md) |
| Zone resolution | No zone is resolved or returned by the real, used serviceability check | — | — | — | — | Not displayed (nothing real to display) | — | MISSING_BACKEND (in the flow actually used) |
| City-tier resolution | Same — not resolved or returned by the real, used serviceability check (city tier only appears in a separate pricing-floor lookup, out of this sprint's scope) | — | — | — | — | Not displayed | — | MISSING_BACKEND (in the flow actually used) |
| `available_provider_count` | Real field, present in the response | — | Parsed | — | — | **Not rendered in the UI** — an internal operational number, not customer-facing per product judgment (CUSTOMER-L5-07 §26's "do not display internal provider counts unless product-approved") | tested (parsed, not rendered) | MATCHED (parsed, deliberately not surfaced) |

## SLA

| Concept | Backend contract | Status |
|---|---|---|
| Selectable SLA options with IDs/labels/windows | **Does not exist anywhere** — no model, no endpoint, no enum | MISSING_BACKEND — not built; see known-gaps.md |
| `TenantServiceAreaService.sla_minutes` | Real column, but never exposed by any customer-facing endpoint (confirmed by grep — zero references outside `serviceability/models.py`) | MISSING_CLIENT is the wrong label here — this is genuinely unreachable data, not merely unconsumed |
| `preferred_date` | Real, unvalidated draft field (`Date`), accepted by the real `PUT` endpoint | MATCHED — implemented as a simple date field, no fabricated availability calendar |
| `preferred_time_window` | Real, unvalidated free-text draft field (`String(50)`), accepted by the real `PUT` endpoint, never validated against any option set anywhere in the backend | MATCHED — implemented as a short free-text field with honest placeholder copy ("e.g. Morning, Afternoon, or a specific time"), not a fabricated multiple-choice SLA selector |

## Error Model

Both engines raise `ServiceOSException` with real, stable string codes
(`CUSTOMER_ADDRESS_NOT_FOUND`-equivalent via `NotFoundException`,
`ERR_INVALID_ZIPCODE`, `ERR_INVALID_CITY`, `HOME_BOOKING_ADDRESS_REQUIRED`,
`HOME_BOOKING_CATEGORY_INVALID`, `HOME_BOOKING_OFFERING_INVALID`,
`NO_PROVIDER_IN_ZIPCODE`, `NO_PROVIDER_IN_CITY`), mapped by this app's
existing `normalizeApiError` (unmodified) into the stable `ApiErrorCategory`
union — only new customer-facing message mappings were added (see
failure-matrix.md).
