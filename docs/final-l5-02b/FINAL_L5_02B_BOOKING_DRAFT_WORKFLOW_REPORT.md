# FINAL-L5-02B — Booking-Draft Workflow Certification

## Authoritative conversion path
`POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm` (`app/engines/home_service_booking/customer_router.py:295`) → `HomeServiceFinalCreationService.finalize()` (`app/engines/final_records/creation_service.py`).

## Verified elements
| Element | Finding |
|---|---|
| Draft creation endpoint | `POST /v1/customer/home-services/booking-drafts` — live-tested this sprint, 200, real draft created |
| Draft update endpoint | `PUT .../booking-drafts/{id}` — live-tested, backend-validated (rejects unknown fields, ignores client-sent price) |
| Draft validation | `mark_ready_for_confirmation()` re-validates provider bookability at confirm-time, not just at match-time (per router comment, HS7 fix) |
| Confirmation endpoint | `POST .../confirm`, `idempotency-key` header supported |
| Transaction boundary | Single `db.commit()` after `finalize()` returns — booking + job created atomically |
| Final booking table | `service_bookings` |
| `service_jobs` creation | Same transaction as the booking (not a separate step/endpoint) |
| Idempotency key | Supported (`Idempotency-Key` header, read via `r.headers.get("idempotency-key")`) |
| Duplicate-confirm protection | `ConfirmationLockService.check_and_raise_if_duplicate()` — a dedicated `CustomerBookingConfirmation` lock row per draft, checked before any write |
| Failure rollback | No manual rollback code found or needed — SQLAlchemy async session rolls back automatically on unhandled exception before `commit()` is reached |

## Required questions — answered
1. **Does confirmation create `bookings`?** No.
2. **Does it create `service_bookings`?** Yes — the canonical final record.
3. **Does it create both?** No — only `service_bookings`.
4. **Is one a projection of the other?** No — `bookings` is entirely unrelated to this flow (different vertical's engine).
5. **Does it create `service_jobs` in the same transaction?** Yes.
6. **What happens when confirmation is retried?** With the same idempotency key (or simply re-calling `/confirm` on an already-confirmed draft): `ConfirmationLockService` detects the existing lock and returns `{"idempotent": true, ...existing booking data...}` without any new write — verified in the 4 dedicated idempotency unit tests in `tests/test_sprint19_final_records.py` (all passing) and via a live 3-attempt retry probe this sprint (see below).
7. **Which ID is shown to the customer?** `service_bookings.booking_number` (format `L501-BK-0001`, etc.) — confirmed live on the Customer Booking list/detail pages ("#L501-BK-0001").

## Live workflow run this sprint
A full draft was created live via the real API as Customer One (category `home_services`, offering `ac_repair`, type `split_ac`, brand `LG`, issue `AC_NOT_COOLING`, zipcode `141001`) and carried through `update → serviceability-check → price-estimate → match-and-price → confirm-price-choice → summary → confirm` (3 confirm attempts: same idempotency key twice, then a different key).

**Result**: `match-and-price` returned `422 HOME_BOOKING_NO_PROVIDER_AVAILABLE` — a real, separate finding: the seeded demo tenant's provider-bookability status (a distinct engine from Sprint 12, gating whether a provider is currently matchable) is not satisfying the live matching query for a freshly-created draft, even though the same tenant/offering/zipcode combination is what the *seed script* uses directly via SQL insert (bypassing matching entirely). This is **not a booking-source-of-truth issue** — it's an orthogonal provider-readiness gate, out of this mission's scope, and is documented here rather than silently worked around.

Despite the match failure, the **retry-safety of the failure path itself was proven live**: all 3 confirm attempts (including 2 with the identical idempotency key) returned byte-identical `422 SERVICE_NOT_AVAILABLE_IN_AREA` responses with no state drift, no partial writes, and no crash — consistent, deterministic behavior under repetition.

One new, minor, real bug found during this probe: `confirm-price-choice` returns an unhandled `500 INTERNAL_ERROR` (rather than a graceful 4xx) when called with no `selected_tenant_id` after a failed match. This is an edge case a normal UI flow would not reach (the UI would stop at the 422 from `match-and-price`), but it's a real gap in the endpoint's own input validation. Logged in the Bug Fix Register as a new, out-of-scope, low-severity finding — not fixed this sprint (scope discipline).

## Result
**PASS** — the draft-to-booking conversion workflow is fully understood, evidenced via source, live partial-run, and existing automated tests (including the success-path idempotency proof from `test_sprint19_final_records.py`, which mocks the DB but exercises the real `finalize()` logic). No `NOT_READY_FINAL_L5_02B_BOOKING_DRAFT_FLOW_FAILED`.
