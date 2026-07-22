# Selected Module — Explicit Boundaries

## In scope for Slice 2F-20
- All 6 mutation routes in `app.engines.compliance.provider_router`.
- The `GET /exports/{export_id}/download` state-mutating read (flagged as
  an alternate-shape mutation).
- The `withdraw_consent` → `service.py`'s `revoke_consent`/`withdraw_consent`
  chain's `tenant_id=None` hardcoding — a DIRECTLY connected defect in the
  service layer this router calls, not a separate module.
- Object-ownership enforcement consistency across all 6 routes (currently
  4 of 6 have an inline `metadata_json` check; `withdraw_consent` has
  none at all; `generate_export`/`cancel_my_request`/`customer_tenant_response`/
  `staff_tenant_response` have it but inconsistently structured — a future
  slice should assess whether to consolidate into a shared helper).

## Out of scope for Slice 2F-20 (do not touch)
- `app/engines/compliance/customer_router.py` — already correctly scoped
  (`require_customer`), not part of this gap.
- Any schema change to `ComplianceRequest`/`ComplianceExport`/`ConsentRecord`
  (no migration permitted per this initiative's standing constraint) — the
  fix must work within the existing `metadata_json` JSONB-key convention.
- DPDP SLA deadline computation, request-type allowlists, status
  state-machine legal transitions — authorization/ownership only.
- The out-of-router export-generation worker/process itself (only the
  QUEUEING route, `generate_export`, is in scope for THIS module's
  closure — the worker is a separate audit surface to be scoped
  explicitly in the implementation slice once located).
- `download_export`'s actual file-serving mechanism (only its dependency/
  authorization is in scope, not its storage/streaming implementation).
- Any other remaining module (`package_commerce`, `customer_reviews`,
  `marketing_automation`, `media_profile`, `profile`, `admin_catalog_*`,
  `analytics`) — queued, not begun.
- `platform_notifications` and all `chat_attachment` media authorization
  (fully closed by the prior six-slice series, not reopened).
- `field_ops`, `Booking`, `quote_checklist`, `invoice_payment`,
  `PartsRequest` closures — all preserved, unmodified.

## No new role, permission, or migration required
`require_tenant_owner_mutation` already exists and admits the EXACT same
role set (`tenant_owner`, `super_admin`) as the currently-used
`require_tenant_owner` — this is a pure dependency swap for 5 of 6 routes,
plus a service-layer fix (passing the real `tenant_id`) for
`withdraw_consent`. No schema change is required to add object-ownership
enforcement — the `metadata_json` convention already exists and is
already used by 4 of the 6 routes; the implementation slice's job is
consistency and the one missing case (`withdraw_consent`), not invention
of a new mechanism.
