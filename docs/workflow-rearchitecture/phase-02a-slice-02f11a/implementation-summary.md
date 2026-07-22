# Slice 2F-11A Implementation Summary

## Scope
Narrow follow-up to Slice 2F-11: close the remaining read-authorization,
privacy, and alternate-route questions for
`app.engines.execution.real_estate_router`.

## Findings

1. **Read-route technician admission was implementation evidence only,
   not product-policy evidence.** `agent_timeline`, `provider_timeline`,
   and `provider_notes` used `require_staff_or_above` (admits
   technician). Slice 2F-11's own reasoning for excluding technician from
   all 11 mutations (no mobile/technician caller exists anywhere for this
   module) applies identically to these 3 reads — there was never
   evidence technician access to reads was intended either; it was simply
   the broadest existing role dependency, reused without re-deriving the
   persona policy for a read context. **Fixed**: added
   `require_owner_or_office_staff_read`, a new, small, local composed
   dependency (same persona set as the mutation guard —
   super_admin/tenant_owner/staff — without the read-only-access-scope
   deny, since a read-only tenant persona must still be able to read).

2. **PII exposure via reads is minimal and already correctly scoped.**
   `RealEstateLeadExecutionEvent.to_dict()` and `RealEstateLeadNote.to_dict()`
   (the actual payloads returned by the 3 provider/agent read routes)
   contain no raw customer PII — only status/notes/actor_role/note_text/
   is_customer_visible. The one place the full `RealEstateLead.to_dict()`
   (including `customer_snapshot`) is returned is `customer_tracking`,
   which is the customer's own record, correctly ownership-filtered.

3. **`customer_tracking` correctly excludes provider-internal
   information**: it never calls `get_timeline` at all (confirmed by
   source inspection), and calls `get_notes(..., customer_only=True)` —
   internal notes and the audit trail are structurally unreachable from
   the customer path, not merely filtered by convention.

4. **`app.engines.real_estate_lead` is a distinct module operating on a
   distinct model** (`RealEstateLeadDraft`, the pre-confirmation
   customer intake/draft flow) — it shares no table, no route, and no
   capability with `execution.real_estate_router`'s `RealEstateLead`
   lifecycle-execution mutations. Classified
   `DISTINCT_MODEL_DISTINCT_CAPABILITY`. No overlap exists to create a
   bypass of the newly-approved security boundary; no modification was
   made or needed there.

## What changed
1. **`app/engines/execution/real_estate_router.py`** — added
   `require_owner_or_office_staff_read`; `agent_timeline`,
   `provider_timeline`, `provider_notes` now use it instead of
   `require_staff_or_above`. All 11 mutation guards, `customer_tracking`
   (`require_customer`), and `admin_router` (`require_super_admin`) are
   unchanged.
2. **New test file**: `tests/test_phase2f11a_real_estate_read_privacy.py`
   (22 tests) — read-route persona matrix, read-only-scope retention,
   tenant isolation on reads, customer-tracking privacy structure, and a
   direct unit test of the new guard's exact role admission.
3. **`tests/test_phase2f11_real_estate_authorization.py`** — the one
   test that had asserted technician was *allowed* on reads
   (`test_technician_allowed_on_reads`) is corrected to
   `test_technician_denied_on_reads`, reflecting the new, evidence-aligned
   policy; the file's docstring is updated to point to this slice.

## What did NOT change
All 11 mutation guards, the per-lead `_assert_agent_owns_lead` assignment
check, the `LEAD_TRANSITIONS` state machine, `customer_tracking`'s
ownership filter, and `admin_router` are unmodified.
`app.engines.real_estate_lead` was inspected but not modified — no
overlapping, weaker, live route was found reaching the same records.
Global tenant mutation coverage is unchanged: this slice's fix is a read
guard, not a tenant-mutation-inventory row (that inventory tracks only
POST/PUT/PATCH/DELETE mutations) — 117/182 preserved exactly.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`.
