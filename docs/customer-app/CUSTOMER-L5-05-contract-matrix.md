# CUSTOMER-L5-05 — Contract Matrix

Verified by direct reading of Python source (no OpenAPI spec, no per-field
Pydantic response models in these engines — field names are literal dict
keys), cross-checked by two independent research passes that reached
identical conclusions.

## The Central Finding

No endpoint anywhere under `app/engines/` initializes a workflow session,
retrieves "the current question," submits an answer for server-side
validation, or recalculates a branch. The concepts in CUSTOMER-L5-05 §5
("initialize booking assistant," "get current question," "submit answer,"
"get next question," "recalculate branch," "retrieve active session,"
"complete diagnostic stage," "cancel assistant session") **do not exist as
backend operations**. This is stated plainly rather than worked around with
an invented client-side "workflow engine" pretending to be backend-driven.

## What Is Real

| Concept | Backend contract | Auth | Client type | API method | Query key | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Issue types (diagnostic) | `GET /v1/customer/catalog/issue-types?category_id=&service_id=` (`admin_catalog/service_option_customer_router.py`, tag "Customer Service Diagnostics") | None | `ValidatedIssueType[]` | `diagnosticsApi.listIssueTypes` | `assistantQueryKeys.issueTypes` | `SingleSelectRenderer` (issue-type step) | `issue-type-schema.test.ts` | MATCHED (category-scoped only — see mismatches) |
| Service options (add-ons) | `GET /v1/customer/catalog/service-options?category_id=&service_id=` (same router) | None | `ValidatedServiceOption[]` | `diagnosticsApi.listServiceOptions` | `assistantQueryKeys.serviceOptions` | `MultiSelectRenderer` | `service-option-schema.test.ts` | MATCHED (category-scoped only) |
| Brands | `GET /v1/catalog/master/brands?category_id=` (`admin_catalog/customer_router.py`) | None | `ValidatedBrand[]` | `diagnosticsApi.listBrands` | `assistantQueryKeys.brands` | `SingleSelectRenderer` (brand step) | `brand-schema.test.ts` | MATCHED (category-scoped only) |
| Service types | `GET /v1/catalog/master/service-types?category_id=` | None | `ValidatedServiceType[]` | `diagnosticsApi.listServiceTypes` | `assistantQueryKeys.serviceTypes` | `SingleSelectRenderer` ("type" step) | `service-type-schema.test.ts` | MATCHED (category-scoped, and the link between offering `requires_type` and this catalog is an inferred, documented assumption — see known-gaps) |
| Photo-required conditional | `requires_photo` on an issue type mapping | — | `boolean` (real field) | — | — | Media-request boundary step | `assistant-steps.test.ts` | MATCHED — the one genuine backend-driven conditional branch in this sprint |
| Description-required conditional | `requires_description` on an issue type mapping | — | `boolean` (real field) | — | — | Short-text follow-up step | `assistant-steps.test.ts` | MATCHED — the second genuine backend-driven conditional branch |
| Offering-level requirement flags | `requires_brand`/`requires_type`/`requires_customer_notes`/`requires_photo_upload` (CUSTOMER-L5-04's `ValidatedOfferingDetail.required_fields`, already fetched) | — | reused, unmodified | — | — | Drives step *presence*, precisely offering-scoped (unlike the catalog data itself) | reused L5-04 tests | MATCHED — the most precise real signal this sprint has for "should this step even appear" |

## What Is Explicitly NOT Real (Not Implemented, Not Faked)

| Concept | Why absent |
|---|---|
| Workflow initialization endpoint | Does not exist |
| Session ID / workflow ID / workflow version | Do not exist — nothing to bind to |
| "Current question" endpoint | Does not exist |
| Answer-submission endpoint with server validation | Does not exist for a diagnostic step in isolation (the closest is `POST /v1/customer/catalog/service-diagnostics/validate`, a single-shot issue+option pair validator against `service_id`/`typed_issue`/`typed_option` — not chained across a session, and again keyed to the ID-mismatched `MasterService`, so not usable against our real `MasterOffering` service ID with confidence) |
| Branch-recalculation endpoint | Does not exist |
| Backend-tracked progress (`current step / total`) | Does not exist — this sprint's "progress" is a client-computed count of the fixed, precomputed step list length (see assistant-architecture.md), never a fabricated backend percentage |
| Boolean question type | No real yes/no diagnostic field exists anywhere in the catalog data — not implemented (would be fabricated) |
| Numeric question type | No real numeric diagnostic field exists — not implemented |
| Long-text question type | Only `requires_customer_notes` (short free text) is real; no long-text field exists |
| Date/time question type | No real field exists |
| Media upload | CUSTOMER-L5-06's scope; this sprint renders the boundary only, never uploads |
| Workflow expiry / version conflict | No workflow to expire or version — not applicable, not fabricated |

## Why Two Different "Issue Type"/"Service Option" Routers Exist

`admin_catalog/customer_router.py` (`/v1/catalog/master/issue-types`) and
`admin_catalog/service_option_customer_router.py`
(`/v1/customer/catalog/issue-types`) both read the same underlying
`MasterIssueType`/`MasterServiceOption` tables but return different shapes —
the second is explicitly tagged "Customer Service Diagnostics" and joins
through `ServiceIssueMapping`/`ServiceOptionMapping` (giving `is_common`,
`is_required`, `is_default` — genuinely more useful, customer-oriented
fields, including real ordering by `is_common` first). This sprint uses the
**second** router for issue types and service options, and the **first**
router for brands and service types (which have no equivalent
"diagnostics"-tagged alternative).

## Entry Payload

Matches CUSTOMER-L5-04's existing `{ serviceId, categoryId }` route params
exactly — no change needed, no full service object, no price, no provider,
no token ever passed through navigation.
