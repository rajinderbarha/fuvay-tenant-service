# Phase 5 — Remaining Blockers

None of these block certification (all hard gates pass; the ticket's own
waiver for environment-limited manual smoke applies). Carried forward,
honestly documented:

1. **No true interactive browser session available** — permanent
   environment constraint, same as every prior sprint. Evidence-based
   smoke substitute used, with the critical approve/reject/credit-issuance
   flow genuinely live-executed (not just inspected).

2. **No dedicated backend "approval readiness gate" engine.** Only (a) a
   frontend-only client-computed checklist and (b) a naive 5-field
   `profile_completion_percentage` hard gate on approve (doesn't check
   documents/deposit/service-areas/staff). Building Module 11's full gate
   spec is a genuine feature addition, not a bug fix — flagged, not
   fabricated as complete.

3. **Three overlapping onboarding subsystems** exist
   (`provider_portal`'s queue, `tenant_engine`'s core lifecycle, and a
   separate self-signup `OnboardingRequest` flow at `/v1/tenants/onboarding/*`)
   — not consolidated this sprint. Each works independently; the critical
   bug fixed this sprint was in the wiring between the first two
   (`provider_portal` → `tenant_engine`).

4. **`request_changes_provider_onboarding` was fixed to delegate to
   `AdminTenantService.request_changes`** instead of raw SQL — but whether
   "changes requested" should affect any approval gate was not further
   investigated (no gate engine exists for it to affect, per item 2).

5. **`activate_tenant` (the simpler `/activate` endpoint) still bypasses
   verification_status and package activation** — a separate, legacy-looking
   lifecycle entrypoint duplicating part of `verify_tenant`'s job. Not
   consolidated (a design decision, not a quick fix).

6. **Service area / staff / suspend / reactivate flows were not
   independently re-tested this sprint** — their code was not touched by
   any bug fix, and time was prioritized on the critical approve→activate→
   credit→ledger chain per this ticket's own stated hard gates.

7. **No dedicated Finance/Read-only/Restricted Admin roles exist** to test
   permission behavior by that literal name (same finding as every prior
   permission-closure sprint) — the underlying `require_permission`
   mechanism was verified live with `tenant_owner` (zero `tenants.*`
   permissions) and works correctly.

None of the above represent a package-activation failure, a duplicate
credit issuance, a bookable-before-approval violation, or a deposit/credit
mixing violation — the four conditions this ticket names as automatic
`NOT_READY`/downgrade triggers. All four were explicitly tested live and
none occurred.
