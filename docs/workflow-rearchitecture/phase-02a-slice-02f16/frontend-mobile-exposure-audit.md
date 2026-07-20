# Frontend and Mobile Exposure Audit

## Callers found
| Application | File | Routes called | Persona |
|---|---|---|---|
| `frontend/tenant-portal` | `lib/api.ts` (lines ~3246-3278) | `/staff/quotes` (create/list/get/items CRUD/send-to-customer/mark-revised/cancel/events), `/staff/checklists` (create/list/get/item-update/complete) | Tenant/provider (web staff/office UI) |
| `frontend/customer-app` | `lib/api/customer-quotes.ts` | `/customer/quotes/*` (jobs list/get/approve/reject/request-revision/events) | Customer |

No mobile app (technician-facing) caller was found for either surface — confirmed via repo-wide search for `provider/quotes`, `staff/quotes`, `staff/checklists`, `customer/quotes` across `frontend/*` and `mobile/*`.

## Requirements checked
| Requirement | Status |
|---|---|
| Provider quote administration is hidden from customers | `frontend/customer-app` has no code referencing `/staff/quotes` or `/provider/quotes` — confirmed by the same search above |
| Customer decisions are hidden from provider personas | `frontend/tenant-portal`'s `lib/api.ts` has no code referencing `/customer/quotes/*` — confirmed |
| Read-only tenant actors see no mutation controls | Not independently auditable from backend-only inspection (would require reading tenant-portal's component-level conditional rendering); backend now denies read-only tenant `access_scope` at the API layer regardless of what the UI renders — the authoritative boundary is enforced server-side (this slice's fix), so a UI bug exposing a mutation button would still be rejected by the backend |
| Technicians see only assigned and supported inputs | No technician caller exists at all for this module's routes — moot |
| Final quotes expose no edit controls | Backend now enforces this server-side (`ITEM_EDITABLE_QUOTE_STATUSES`, this slice's fix) regardless of UI state — the authoritative boundary is the backend, consistent with "backend remains authoritative" |
| Amounts displayed match backend response | `frontend/customer-app/lib/api/customer-quotes.ts`'s `Quote` type reads amount fields directly from the API response — no client-side recalculation found |
| Unsupported PartsRequest approval is not advertised | No frontend code in either caller references `PartsRequest` — confirmed no such capability is advertised through this module's UI |
| Backend remains authoritative | Confirmed — every authorization/ownership/amount/state check enforced this slice lives in the backend service/router layer, not the frontend |

## Minimal corrections made
None required at the frontend/mobile layer — no frontend code needed to change, since the frontend already calls the correct persona-scoped routes (`/staff/*` for provider, `/customer/*` for customer) and never attempted to call the other persona's routes. All fixes this slice were backend-only (authorization, ownership, amount validation, state-lock, privacy filtering). Per this slice's explicit instruction ("Make only minimal policy/state corrections. Do not redesign pages."), no frontend changes were made.

## Conclusion
Not `FRONTEND_MUTATION_SURFACE_ABSENT` — live callers exist for both provider/staff and customer personas, correctly separated at the application level even before this slice's backend fixes (the frontend was never the vector for the authorization gaps found — the backend was silently permissive regardless of what the frontend intended to restrict).
