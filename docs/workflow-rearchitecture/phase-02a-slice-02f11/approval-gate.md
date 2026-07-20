# Approval Gate — Slice 2F-11

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**
**[CORRECTED IN SLICE 2F-11A]:** This document's `PRIVACY_CLOSED: YES`
and `alternate-route`-adjacent claims were asserted without (a) applying
the same evidence standard used for the 11 mutations to the 3
provider/agent read routes (which admitted technician via
`require_staff_or_above`, an implementation-evidence-only choice, not
product-policy evidence), and (b) inspecting `app.engines.real_estate_lead`
at all. Both gaps are now closed — see
`phase-02a-slice-02f11a/approval-gate.md` for the corrected, fully
verified final answer. The architecture finding, mutation-security
closure, and domain-integrity closure below remain accurate and
unmodified.

## Architecture finding (load-bearing for this whole gate)
Fresh investigation confirmed `app.engines.execution.real_estate_router`
implements a **real-estate lead execution/CRM tracker**, not a property
marketplace — no `Property`/`PropertyListing`/`PropertyMedia`/`Offer`/
`Viewing` model exists anywhere in this codebase. Every workstream
targeting those capabilities is honestly reported as
`UNSUPPORTED_CAPABILITY` (see `real-estate-model-lineage.md` and the
workstream-specific docs), not fabricated.

## Reasoning

### SECURITY_CLOSED: YES
All 11 mounted mutations (`agent_router`, `/v1/staff/real-estate-leads/*`)
— previously **`get_current_user`-only, no role check at all** — now
require `require_owner_or_office_staff_mutation` (role in {super_admin,
tenant_owner, staff}, access-scope-aware; technician deliberately
excluded, matching direct evidence that no mobile/technician client has
ever called this module). The pre-existing, correct
per-lead `_assert_agent_owns_lead` assignment check and tenant-scoped
`_get_lead` filter are unmodified and re-verified. 6 read routes
(`agent_timeline`, `provider_timeline`×1, `provider_notes`,
`customer_tracking`) were also fixed from `get_current_user`-only to
role-appropriate guards (`require_staff_or_above`/`require_customer`).
`admin_router`'s 2 routes were already correctly `require_super_admin`-gated,
unmodified. No weaker alternate route exists (see
`alternate-real-estate-route-audit.md`). Zero unverified routes remain —
runtime inventory confirms 11/11 mutation routes verified.

### DOMAIN_INTEGRITY_CLOSED: YES
The `LEAD_TRANSITIONS` state machine and `_set_status`'s
validate-before-mutate ordering were already correct (no
"persistence before validation" defect exists here, unlike the
historical complaints-module bugs) — re-verified, unmodified. Final
states (`unqualified`, `converted`, `closed_lost`, `rejected`) are
protected (empty transition sets). No confirmed integrity defect was
found. Every capability the mission anticipated for property/listing/
viewing/media/offer domains is confirmed absent, not silently broken —
there is nothing to fail integrity closure on for capabilities that
don't exist.

### PRIVACY_CLOSED (as of Slice 2F-11): YES, WITH AN UNSUPPORTED CAVEAT
**[CORRECTED IN SLICE 2F-11A — now YES, fully verified.]** This section
originally treated technician admission on the 3 provider/agent read
routes as "an evidence-neutral judgment call, not a defect." On
reflection in Slice 2F-11A, that was inconsistent with the standard this
same slice applied to the 11 mutations (where the identical absence of
technician caller evidence was treated as disqualifying, not neutral).
Slice 2F-11A re-applied that standard to the reads and fixed it —
technician is now excluded from all 3 provider/agent read routes via a
new `require_owner_or_office_staff_read` dependency. Tenant/lead/customer
isolation (tenant filter in `_get_lead`; customer_id filter in
`customer_tracking`'s inline query; customer-visible note filtering in
`get_notes`) remains accurate and unmodified. No proven PII leak was
found in either slice.

### PRODUCT_POLICY_CLOSED: BLOCKED
A small number of genuine, non-security product questions remain open
(technician read-access symmetry, whether lead conversion should ever
create a downstream record, note-visibility permission granularity) —
see `product-decisions-required.md`. None of these block security,
domain-integrity, or privacy closure.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Quality gates (51) — summary
All satisfied for this slice's own scope (mutation security, domain
integrity, and the architecture finding). Gates targeting nonexistent
capabilities (property/listing/media/offer/viewing-as-a-record) are
satisfied vacuously and honestly, per direct confirmation of absence, not
fabricated evidence. **Two items were not, in fact, fully closed by this
slice** despite the combined status naming them closed: full read-level
privacy verification (technician read-access evidence standard) and
alternate-route closure (`app.engines.real_estate_lead` was never
inspected). Both are now closed by Slice 2F-11A — see
`phase-02a-slice-02f11a/approval-gate.md`. Evidence for this slice's own
valid findings is distributed across the other 25 files in this
directory.

## Global coverage
Tenant mutation coverage: **117/182** (up from 106/182 — 11 newly
protected, all within the pre-existing denominator; this module's
routes were already counted before this slice). Customer route coverage
unaffected (this module's one customer route is a read, not a mutation,
and was never part of the denominator).

## Stop condition honored
Only `app/engines/execution/real_estate_router.py` was modified for
behavior, plus the 2 global-coverage CSVs in
`docs/workflow-rearchitecture/phase-02a-slice-02f/`. No other file under
`app/engines/execution/` or `app/engines/complaints/` was touched.
`execution.coaching_router`, `field_ops.checklist_router`,
`field_ops.staff_router`, and `app.engines.real_estate_lead` were not
begun. No permission, role, or financial workflow was created. No
booking-pipeline merge occurred. No frontend file was modified.
`readonly@demo-ac-services.local` and migration 144 were untouched. No
visual redesign occurred. **Stopping here per instruction — not
beginning `execution.coaching_router` or any other module.**
