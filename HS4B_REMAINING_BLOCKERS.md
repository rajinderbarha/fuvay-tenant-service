# HS4B — Remaining Blockers

1. **Permission-aware UI not implemented** — same gap documented across
   HS2/HS3/HS4; backend authorization is real (`P.TENANT_UPDATE`,
   `require_tenant_owner`), frontend doesn't conditionally hide
   Publish/Save/Refresh based on permission.
2. **Setup checklist visual confirmation not performed** — the data
   contract is confirmed fixed and correct (checklist already reads
   `providerStatusApi.get()`), but no browser session verified the
   rendered checklist page updates visually.
3. **Availability-configured check is coarse** — checks
   `provider_availability_rules.is_active=true` count > 0, not
   specifically "at least one **open day**" as the ticket's check #9
   distinguishes from check #8 ("availability configured"). Treated as
   one combined check.
4. **Staff/technician-configured check not implemented** — the ticket's
   bookability check #12 ("Staff/technician configured if required")
   was not added to `_evaluate_provider_bookability` — no clear signal
   exists for "is a technician required for this tenant's services,"
   and adding it without that distinction risked over-blocking tenants
   who don't need staff. Documented as a deliberate omission, not a
   silent gap.
5. **`is_visible` policy is a product judgment call, not a spec** — the
   ticket says "may be visible only if... depending on product policy"
   and asks to "document final policy clearly," which this sprint did
   (see Bookability Refresh Fix Report), but this is an interpretation,
   not a certainty — a different policy owner might set the bar
   differently (e.g., requiring is_bookable-equivalent for visibility
   too).
6. **`npm run build`/`lint`/`test` not run** — established constraint,
   `tsc --noEmit` used as the build-health gate throughout this session.

## What is solid and fixed this sprint
- The core, ticket-defining bug — `POST /v1/provider/status/refresh`
  being a no-op — is genuinely fixed with real computation reading 5
  real tables, persisting to the real pre-existing
  `provider_visibility_statuses` table, live-verified across 6 distinct
  scenarios including both directions of the suspended-tenant gate.
- All 5 named hard gates (service area, availability, usage credits,
  security deposit, suspended tenant) are enforced and individually
  live-verified.
- Frontend now calls refresh immediately after publish and shows
  accurate bookable/not-bookable copy with real blocking reasons — never
  a fabricated "ready" state.
- Zero regressions across 586 test executions in 4 separate sweeps.
- TypeScript clean.
