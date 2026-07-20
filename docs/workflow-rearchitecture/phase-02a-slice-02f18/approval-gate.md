# Slice 2F-18 Approval Gate

> **ADVANCED BY SLICE 2F-18A.** The technician tenant-wide access,
> attachment-ownership, and thread-error-privacy gaps that justified this
> slice's `DOMAIN_INTEGRITY_BLOCKED` status are now closed — see
> `docs/workflow-rearchitecture/phase-02a-slice-02f18a/`. Coverage remains
> 200/226 (unchanged — this was router-level, not object-level, arithmetic).
> Nothing in this slice's own findings was found incorrect; this notice
> records progression to a stronger final status, not a correction.

## Final status

**SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED**

## Why SECURITY_CLOSED
- All 10 selected mutation routes (plus their 10 associated reads) are
  classified with exactly one capability and one persona each
  (`provider-router-final-route-inventory.csv`, `notification-persona-policy.csv`)
  — no combined/dual-persona label used.
- Every tenant/provider mutation is mutation-scope protected
  (`require_owner_or_office_staff_mutation` for `provider_*`,
  `require_staff_or_technician_only` for `staff_*`) — confirmed live via
  runtime introspection, not source-reading alone
  (`runtime-verification-report.md`).
- Only canonical roles are admitted by both dependencies (existing,
  reused, unchanged dependencies — no new role or alias introduced).
- Tenant, thread, message, and record ownership are enforced: the
  cross-tenant/cross-customer chat-thread substitution bug found during
  investigation is fixed (`implementation-summary.md` finding 3,
  `TestChatThreadRecordOwnership`).
- Sender impersonation is impossible — proven directly, not merely
  asserted (`sender-identity-authority.md`, schema-level field-absence
  test).
- Arbitrary/cross-tenant recipient targeting is impossible — no recipient
  identifier exists on any route in this router at all
  (`recipient-authority.md`); the one record-reference input
  (`record_id`) is now ownership-validated.
- No weaker same-record route remains — the `customer_router.py` alternate
  route (same tables, same service methods) is fixed alongside
  (`alternate-notification-route-audit.md`).
- Runtime verification exits zero (`runtime-verification-report.md`, this
  slice's 49-test suite passing).

## Why DOMAIN_INTEGRITY_BLOCKED (not closed)
- **Technician assignment-limiting is explicitly deferred**, not
  implemented — `staff_chat_router`/`staff_notif_router` remain
  tenant-wide for staff AND technician callers by design (pre-existing,
  intentional, relied upon by 2 live frontend surfaces — see
  `staff-technician-communication-policy.md`,
  `product-decisions-required.md` item 1). Workstream 10's requirement to
  enforce "assigned technician only... where genuinely supported" cannot be
  honestly marked closed while this gap is open by product-policy
  necessity rather than by omission.
- Two smaller, non-blocking gaps are also open (media-attachment ownership,
  thread-access error-code distinguishability) — neither is a content-leak
  or an authorization bypass, both flagged in
  `product-decisions-required.md`/`known-limitations.md`.

`PRIVACY_CLOSED` and `GLOBAL_COVERAGE_CLOSED` conditions ARE independently
satisfied (no internal content reaches customers via the now-enforced
visibility rules; canonical CSVs recount identically at 200/226) but the
combined final-status vocabulary offered by this mission does not have a
"security+privacy+coverage closed, domain-integrity blocked" option, so the
most conservative available label,
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`, is used — it does not overstate
closure.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied.
- No new role, permission, or alias added.
- All previously-approved tests still pass (see `test-report.md`,
  `regression-report.md`).

## Coverage
**190/226 → 200/226.** 26 unprotected tenant/provider mutation routes
remain, across the 10 non-selected modules ranked in
`remaining-module-queue-update.csv`.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No `My Work`/
`Next-Action` work was built. No frontend/mobile file was modified. No
attachment, email/SMS/push, or WebSocket infrastructure was built. No
second, unrelated module's authorization was begun — `customer_router.py`
was fixed only because it is the same module directory reaching the exact
same records via the exact same service methods (a same-record bypass, not
a second module).

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18 approval gate. The remaining 26-route, 10-module queue
(`remaining-module-queue-update.csv`) is left for a future slice; no
implementation of any other module has begun.
