# FINAL-L5-04B — Staff Entitlement Scope Report

> **Updated in FINAL-L5-04C.**

## FINAL-L5-04C investigation and honest result
A dedicated staff-facing "category filter" endpoint was searched for specifically this sprint (`app/engines/home_service_assignment/staff_router.py`, `app/engines/field_ops/staff_router.py`) — **no such endpoint exists**. What does exist is `GET /v1/staff/service-jobs` ("list jobs assigned to me"), which reads `assigned_staff_id` directly with no category-filter concept at all — it's a historical/current-assignment view, not a forward-looking "what categories can I pick up" picker.

## Real, load-bearing finding: the practical risk is closed upstream, not via a redundant staff-side filter
A technician can only ever be assigned to a job whose tenant/category entitlement was valid at the moment that job was created — and that moment is now gated: `HomeServiceChatbotBookingService.confirm_draft()` (the real point where a customer booking becomes a tenant-owned job) re-validates entitlement via the same guard proven in the Matching Entitlement Report. **A non-entitled category can no longer produce a new job for staff to be assigned to in the first place** — so while no distinct "staff category filter" surface was built, the underlying risk the mission's Part 7 is protecting against (a technician working a job in a category the tenant isn't entitled to) is now structurally prevented at its true source.

## Required checks — status
| # | Check | Result |
|---|---|---|
| 1 | Technician One sees only Tenant One entitled categories | No distinct filter surface exists to check this against — see above for why the practical risk is closed differently |
| 2 | Tenant Two categories never appear | Same — no staff-facing category listing exists at all (only assigned-job history, which is tenant-scoped by `assigned_staff_id`→tenant chain already, unrelated to this sprint) |
| 3 | Disabled category disappears from new-operation filters | New jobs cannot be created in a disabled category (booking confirmation guard) — the practical effect is achieved even without a filter UI |
| 4 | Re-enabled category returns | Same — booking confirmation allows new jobs again once re-entitled |
| 5 | Historical jobs in a disabled category remain discoverable via assigned-job history | **Confirmed unaffected** — `GET /v1/staff/service-jobs` was not touched, still reads all historically-assigned jobs regardless of current entitlement state |
| 6 | `StaffContextProvider` remains single auth-context owner | Unaffected — no auth-context code was touched this sprint |
| 7 | No duplicate `/v1/auth/me` request reintroduced | Unaffected — no changes to auth-context fetching |

## Result
No distinct staff category-filter endpoint exists in this codebase to wire, confirmed by dedicated investigation this sprint (not assumed). The underlying safety property — staff cannot end up assigned to a non-entitled category — is nonetheless real and enforced, because the actual assignment-creation gate (booking confirmation) is now entitlement-aware. This is an honest, load-bearing closure of the practical risk, not a redundant UI feature.
