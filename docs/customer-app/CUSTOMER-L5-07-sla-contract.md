# CUSTOMER-L5-07 — SLA Contract

## There Is No Real SLA Contract to Document

This is stated as the document's primary content, not a gap buried in a
footnote — matching the honesty pattern established for CUSTOMER-L5-05's
"no workflow engine" and CUSTOMER-L5-06's "no draft versioning" findings.

An exhaustive, case-insensitive grep for `sla` across the entire backend
returned 60 files, almost all unrelated (support-ticket SLA timers,
final-record summaries, permission strings). The **only** directly
relevant hit is:

```python
# app/engines/serviceability/models.py
class TenantServiceAreaService(ServiceOSBase):
    ...
    sla_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

This is an admin-set integer on a tenant's own service-area/service
mapping row. It is:

- **Never exposed by any customer-facing endpoint** — confirmed by grep:
  zero references to `sla_minutes` outside `serviceability/models.py`
  itself. It is not in the real draft serviceability-check response, not
  in `get_available_services_for_address` (which does read it internally
  but only for the general, unused serviceability engine — see
  serviceability-architecture.md), and not in any schema the booking-draft
  flow returns.
- **Not a set of selectable options.** There is no model, enum, or
  endpoint representing "same day / 24h / 48h / 72h / 96h" or any other
  customer-choosable window. `sla_minutes` is a single, backend-internal
  configuration value per tenant-service mapping.

## What Is Real: `preferred_date` and `preferred_time_window`

The booking draft has two genuine, backend-accepted fields for scheduling
intent:

| Field | Backend type | Validation | This sprint's implementation |
|---|---|---|---|
| `preferred_date` | `Date`, nullable | None found — accepted as-is by the real `PUT` endpoint | Not collected this pass (see known-gaps.md — a date picker was judged lower priority than the address/serviceability core given this sprint's already-large scope) |
| `preferred_time_window` | `String(50)`, nullable | **None** — no enum, no format check, no option-set anywhere in the backend | A short free-text field (`ServiceabilityScreen`), honestly labeled with placeholder copy ("e.g. Morning, Afternoon, or a specific time") rather than presented as a validated multiple-choice selector |

## Why No SLA-Options UI Was Built

Building a "Same day / 24h / 48h / 72h / 96h" selector — as the sprint
prompt's aspirational model describes — would mean either (a) inventing
option values with no backend enum to match, submitting a string the
backend would accept but never validate or act on, or (b) fabricating a
mapping from those labels to `sla_minutes`, a field the customer-facing
API cannot even see. Both would violate CUSTOMER-L5-07 §72's "do not
hardcode SLA options" and "do not fabricate next available time"
prohibitions directly. The honest choice — implemented — is a plain text
field that maps 1:1 to the one real, unvalidated field the backend
actually has.

## Draft Mapping

`preferred_time_window` is written via the same real `PUT` endpoint
already used for `address_id` — no new endpoint, no new field-acceptance
gap (unlike `issue_type_id`/`service_option_ids_json` from CUSTOMER-L5-06,
`preferred_time_window` **is** in the `PUT` endpoint's accepted-field
list).

## Test Coverage

Not applicable in the sense of "SLA option selection tests" — there are
no options to test selecting. The free-text field is covered indirectly
through the existing draft-update mutation tests (CUSTOMER-L5-06) and this
sprint's `ServiceabilityScreen` integration into the real draft-update
call.

## What Would Close This Gap

Real backend work: a customer-facing SLA/window-option endpoint backed by
an actual enum or configuration table, wired to `sla_minutes` or a
successor field, with real capacity/expiry semantics. Out of scope for a
frontend sprint.
