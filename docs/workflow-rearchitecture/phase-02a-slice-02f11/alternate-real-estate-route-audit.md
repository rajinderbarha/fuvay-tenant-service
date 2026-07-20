# Alternate Real-Estate Route Audit — Slice 2F-11 (Workstream 14)

## Method
Grepped every reference to `RealEstateLead` repository-wide (excluding
tests) to find any alternate route reaching the same lead-lifecycle
mutations this slice fixed.

## Findings

| Module | Capability | Disposition |
|---|---|---|
| `app.engines.execution.real_estate_router` (this slice) | Lead lifecycle mutations (accept/reject/contact/etc.) | CANONICAL_PROVIDER_LEAD_WRITE — sole implementation, now fixed |
| `app.engines.final_records.provider_router` | `GET /v1/provider/my-records/leads` — list/detail only | DISTINCT_CAPABILITY — read-only, no `.status =` mutation anywhere in this file (confirmed by grep); not an alternate write path |
| `app.engines.final_records.admin_router` | `GET /v1/admin/final-records/leads` — platform-wide list/detail | DISTINCT_CAPABILITY — read-only, already platform-admin-gated (unmodified, out of scope) |
| `app.engines.real_estate_lead.customer_router` | Customer-facing lead **draft/intake creation** (pre-confirmation) | DISTINCT_CAPABILITY — an entirely separate module handling lead *creation*, not lifecycle *execution*; explicitly out of scope ("do not begin another real-estate module") — not audited further this slice |
| `app.engines.complaints.eligibility_service` / `app.engines.customer_reviews.eligibility_service` | Reference `RealEstateLead` only as one of several valid `record_type` options for complaint/review eligibility (read-only lookup) | DISTINCT_CAPABILITY — unrelated to lead execution, already closed in Slice 2F-9/2F-10/2F-10A |
| `app.engines.platform_notifications.recipient_resolver` | Resolves notification recipients for lead-related events | TRUSTED_INTERNAL — not a mutation path |

## No weaker live route found
Every capability this slice's mutations perform
(accept/reject/contact/follow-up/site-visit/qualify/disqualify/convert/
close-lost/notes) has exactly one implementation, now fixed. No
alternate or legacy route reaches the same service methods with weaker
checks.
