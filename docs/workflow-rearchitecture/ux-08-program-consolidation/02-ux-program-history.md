# UX-08 Workstream 2: UX Program History (UX-01 through UX-07)

Status: CONSOLIDATED-FROM-PRIOR-EVIDENCE. Every status token below was
located verbatim in the cited phase's own `approval-gate.md` (or, where that
file did not carry a canonical status token, the nearest equivalent
status/summary doc in that phase's directory) inside this worktree, checked
by direct `grep`/`Read` this pass. No historical status is reinterpreted or
upgraded — this is a transcription/synthesis exercise, not a re-audit.

## UX-01: Foundation (`docs/design/ux-01-foundation/`)

- **Final status: `FRONTEND_BUILD_BLOCKED`** (source:
  `docs/design/ux-01-foundation/approval-gate.md`).
- Design-foundation-level work; the phase never reached a runnable build in
  its own environment, so functional claims beyond source review were never
  certified.

## UX-02: Super Admin (`docs/design/ux-02-super-admin/`)

- **Final status: `SUPER_ADMIN_SOURCE_FOUNDATION_COMPLETE_FRONTEND_BUILD_BLOCKED`**
  (source: `docs/design/ux-02-super-admin/implementation-summary.md`).
- Source-level design foundation considered complete, but — like UX-01 — the
  phase closed without a verified `npm install`/`tsc`/`vitest`/`next build`
  chain in its own environment (see that phase's
  `environment-blocker-report.md`, `build-command-manifest.md`). UX-08
  Workstream 14 (test reconciliation) re-attempts `vitest` for super-admin
  fresh in this pass — see doc 03.

## UX-03: Tenant Portal (`docs/design/ux-03-tenant-portal/`)

- **Final status: no single canonical status token was found in this
  worktree.** Searched `approval-gate.md` and every other `.md` file in
  `docs/design/ux-03-tenant-portal/` for a `_COMPLETE`/`_PARTIAL`/`_BLOCKED`
  style token (the convention used by every other phase); none matched.
  `approval-gate.md` only lists open checklist items (product sign-off,
  build verification, backend contract confirmation, a11y pass) without a
  headline verdict.
- Honest treatment: recorded here as **UX03_STATUS_TOKEN_NOT_LOCATED** —
  this is a genuine documentation gap in the historical record, not
  something UX-08 should paper over by inventing a plausible-sounding
  status. Superseded in practice by UX-04, which continues tenant
  operations from this same design-foundation baseline.

## UX-04 / UX-04A / UX-04B: Tenant Operations (three sub-phases)

- **UX-04 (`docs/design/ux-04-tenant-operations/`) final status:
  `TENANT_OPERATIONS_DESIGN_PARTIAL`** (source: that phase's
  `approval-gate.md`).
- **UX-04A (`docs/design/ux-04a-tenant-operations-completion/`) final
  status: promoted to `TENANT_OPERATIONS_DESIGN_COMPLETE`** for the frontend
  design-foundation scope (source: that phase's `approval-gate.md`).
- **UX-04B (`docs/design/ux-04b-runtime-certification/`) final status:
  confirms/holds `TENANT_OPERATIONS_DESIGN_COMPLETE`**, adding a runtime
  certification pass on top of UX-04A's design-completion claim (source:
  that phase's `approval-gate.md`).
- Net: tenant operations design work progressed PARTIAL -> COMPLETE across
  three sub-rounds, with the final `TENANT_OPERATIONS_DESIGN_COMPLETE`
  landing at commit `7488335` (UX-04 final, per this pass's Workstream 1
  ancestry check).

## UX-05: Staff/Technician App (`docs/design/ux-05-staff-technician-app/`)

- **Final status (Round 7): `STAFF_TECHNICIAN_APP_DESIGN_PARTIAL`** (source:
  that phase's `approval-gate.md`, explicitly states why this is not
  `STAFF_TECHNICIAN_APP_DESIGN_COMPLETE`).
- Per user's existing memory (`project_ux05_backlog_bl001.md`), an open,
  low-priority, non-blocking backlog ticket exists for the remaining
  Staff/Technician dev showcases (~18/30 done) — logged, not executed. This
  is consistent with the PARTIAL final status and is not re-litigated here.
- Landed at commit `493a132` (UX-05 final, confirmed ancestor of `50fe95b`
  per Workstream 1).

## UX-06: Customer App (`docs/design/ux-06-customer-app/`)

- **Final status: `CUSTOMER_APP_DESIGN_COMPLETE`** (source: that phase's
  `approval-gate.md`, which states this explicitly and notes "the remaining
  path to full `CUSTOMER_APP_DESIGN_COMPLETE` is narrow" in earlier rounds
  before closing complete).
- Per the UX-08 brief's explicit instruction, this status is **not**
  second-guessed or downgraded here — it really was complete at its own
  closure. UX-07 later iterated further on top of this baseline (dark mode,
  IA rebuild, accessibility fixes for the SmartBot/nav) but that is
  additive improvement, not evidence the UX-06 closure claim was wrong.
- Landed at commit `b426e08` (UX-06 final, confirmed ancestor of `50fe95b`
  per Workstream 1), later merged into the UX-07 branch at merge commit
  `5461f6c`.

## UX-07: Cross-App Production Readiness (`docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/`)

- **Final status: `UX07_INTEGRATION_PARTIAL`** (source: that phase's
  `approval-gate.md`).
- Per the UX-08 brief's explicit instruction, this status **stays**
  `UX07_INTEGRATION_PARTIAL` — it is not rewritten as more complete than it
  was, even though this UX-08 pass performs additional verification on top
  of it.
- UX-07 ran across multiple rounds/passes (Round 1 through Pass 3f), adding:
  theme foundation (System/Light/Dark) for customer-app, dark-mode migration
  across ~11 customer screens, a customer Home IA rebuild, SmartBot category
  handoff, bottom-nav narrowing, accessibility fixes for SmartBot and the
  bottom nav, and a cross-app workflow verification (booking
  `BK-20260721-000008` -> job `JOB-20260721-000008` -> completed ->
  review `REV-56700400`, commission -21.0) referenced in Round 3 evidence and
  reused (re-verified where feasible) in UX-08 Workstream 6 of this pass.
- This is the commit (`50fe95b`) UX-08 branches from.

## Net program trajectory

| Phase | Scope | Final status | Commit |
|---|---|---|---|
| UX-01 | Foundation | FRONTEND_BUILD_BLOCKED | (pre-UX-02) |
| UX-02 | Super Admin | SUPER_ADMIN_SOURCE_FOUNDATION_COMPLETE_FRONTEND_BUILD_BLOCKED | (pre-UX-03) |
| UX-03 | Tenant Portal | UX03_STATUS_TOKEN_NOT_LOCATED (gap) | (pre-UX-04) |
| UX-04/4A/4B | Tenant Operations | TENANT_OPERATIONS_DESIGN_COMPLETE | 7488335 |
| UX-05 | Staff/Technician App | STAFF_TECHNICIAN_APP_DESIGN_PARTIAL | 493a132 |
| UX-06 | Customer App | CUSTOMER_APP_DESIGN_COMPLETE | b426e08 |
| UX-07 | Cross-App Production Readiness | UX07_INTEGRATION_PARTIAL | 50fe95b |
| UX-08 | Program Consolidation (this pass) | see release baseline matrix, doc 10 | (in progress) |

No phase's historical status is altered by this document. Where a build
environment blocker (UX-01, UX-02) was never resolved by that phase's own
closure, UX-08 Workstream 3 (test reconciliation) attempts a fresh
verification in this pass's environment and reports the real, current
result rather than assuming the old blocker persists or has cleared.
