# Approval Gate — Slice 2F-9B

## Status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Reasoning

### AUTHORIZATION_CLOSED: YES
No backend authorization file was modified this slice. All 9 provider
complaint mutations remain gated by `require_tenant_owner_mutation`; the
4 service-layer ownership fixes from Slice 2F-9 remain intact; role,
access-scope, and ownership enforcement re-confirmed passing (114
targeted + 681 broader-partition tests). Runtime inventory: 9/9 verified,
0 unverified. See `backend-regression-report.md`.

### DOMAIN_STATE_INTEGRITY_CLOSED: YES
`FINAL_STATUSES`, `ALLOWED_TRANSITIONS_EXT`, `_transition`,
`provider_add_response`, and `provider_offer_resolution` are unchanged
from Slice 2F-9A. Illegal-state resolution attempts remain side-effect
free (re-verified, unmodified tests still passing). Audit events remain
correctly logged only on success.

### AUDIT_CLOSED: YES
`EVT_PROVIDER_RESPONDED` and `EVT_RESOLUTION_PROPOSED` logging behavior
is unchanged and re-verified passing.

### FRONTEND_STATE_POLICY_ALIGNED: YES
This is the gate this slice exists to close, and it is now closed
exactly, not partially:
- **Offer Resolution appears only in exact backend-legal source states**:
  `canOfferProviderComplaintResolution` gates the button on exactly
  `awaiting_provider_response`/`under_admin_review`, derived directly
  from `ALLOWED_TRANSITIONS_EXT` (see `backend-resolution-source-states.md`),
  proven via 22 direct helper tests covering every real complaint status
  plus missing/unknown-status cases (`frontend-test-matrix.csv`).
- **Reply visibility matches its backend final-state policy**: unchanged,
  re-verified (`reply-control-regression.md`).
- **Unauthorized personas see no active controls**: staff, technician,
  customer, guest, and unknown roles all return `false` from the helper
  even in a legal state — tested directly.
- **Read-only users see no active controls**: `customer_support_limited`
  access scope returns `false` even in a legal state — tested directly.
- **Unknown/missing status fails closed**: tested directly (empty
  string, `null`, `undefined`, and an unrecognized status string all
  return `false`).
- **Deep links and stale state cannot bypass the frontend gate**: no
  query-parameter or URL-based modal-opening path exists at all
  (structural, source-verified); an already-open modal auto-closes if the
  complaint's refetched state becomes ineligible; the submit handler
  re-checks eligibility immediately before invoking the mutation; the
  `Modal`'s own `open` prop is additionally gated as defense in depth. See
  `deep-link-stale-state-review.md`.
- Every Offer Resolution caller across the repository was inventoried:
  exactly one (`tenant-portal`'s complaint detail page). A superficially
  similar super-admin "Propose resolution" control was found to call a
  structurally distinct, out-of-scope `complaints.admin_router` endpoint
  and was correctly left untouched.

### PRODUCT_POLICY_CLOSED: BLOCKED
One genuine, carried-over product question remains open: whether
`provider_add_response` should also block on `resolved`/`settled`, not
just base `FINAL_STATUSES` (Slice 2F-9A `product-decisions-required.md`
item 1, unchanged, not decided or touched this slice).
`complaints.customer_router`'s own authorization gap also remains open
and out of scope.

## Final combined status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

This distinguishes technical closure (authorization, domain-state
integrity, audit, and now exact frontend state alignment — all fully
verified and passing) from the one remaining, genuinely open product
decision, which does not block any of the technical closures above.

## Quality gates (31) — summary
All 31 satisfied, verified directly (not asserted) — evidence
distributed across the other 14 files in this directory:
`implementation-summary.md`, `backend-resolution-source-states.md`,
`frontend-resolution-state-matrix.csv`, `frontend-helper-design.md`,
`resolution-control-changes.md`, `reply-control-regression.md`,
`deep-link-stale-state-review.md`, `frontend-test-matrix.csv`,
`backend-regression-report.md`, `documentation-corrections.md`,
`product-decisions-required.md`, `test-report.md`,
`known-limitations.md`, `deferred-items.md`.

## Stop condition honored
Only 2 frontend files (`lib/api.ts`,
`app/(tenant)/provider/complaints/[complaint_id]/page.tsx`) and 1 test
file (`lib/api.persona.test.ts`) were changed, plus this slice's own and
Slice 2F-9A's documentation. No backend file was modified — confirmed via
`git status`/`git diff --stat` showing zero changes under
`app/engines/complaints/` from this slice. `complaints.customer_router`,
`complaints.admin_router`, and `execution.real_estate_router` were not
begun or modified. No permission was granted; no new role was
introduced; no visual redesign occurred (2 boolean conditions + 1 effect
+ 1 handler re-check, same layout/styling/fields throughout). **Stopping
here per instruction — not beginning `complaints.customer_router` or any
other module.**
