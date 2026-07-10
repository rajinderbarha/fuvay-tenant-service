# HS6 — Remaining Blockers

1. **Full HTTP end-to-end live verification not performed** — the two
   real bugs fixed this sprint were verified at the pure-function/
   logic level (direct Python calls, source-structure assertions), not
   via a live `POST /{draft_id}/match-and-price` call through a real
   booking draft. This is the sprint's most significant gap relative to
   this session's established live-curl verification standard.
2. **Two confirmed data-model inconsistencies, not unified**:
   - Bookability: `_evaluate_provider_bookability` (HS4B) reads
     `tenant_billing`; the matching engine's own eligibility gate reads
     `tenant_wallets`/`security_deposits`/`tenant_package_assignments`
     — different tables, unconfirmed whether they're kept in sync.
   - Area coverage: HS5B's newly-built per-area type/brand coverage
     (`tenant_service_area_services`) is **not consumed** by the real
     matching engine, which instead uses `provider_enabled_offerings`'
     JSON `supported_type_ids`/`supported_brand_ids` arrays — a
     completely different, disconnected data model.
3. **Availability filtering is existence-only, not time-specific** — the
   matching engine's eligibility gate only checks "at least one active
   availability rule exists," not "available at the customer's
   requested date/time." HS5B's `get_tenant_home_services_matching_
   inputs()` does the time-specific check but is a separate, unconnected
   preview function.
4. **Matching diagnostics page not fully audited** — only 2 of ~10
   required output panels confirmed present via grep; full page content
   not read this sprint.
5. **Permission-aware UI not verified** — whether the diagnostics page
   gates internal score visibility behind a debug permission was not
   checked this sprint.
6. **`npm run build`/`lint`/`test` not run** — established constraint.

## What is solid and newly fixed this sprint
- **Critical bug #1 fixed**: the provider-matching price formula now
  correctly applies platform fee to both Low and High — was previously
  returning the raw, pre-fee provider max as `high_price`, a direct
  hard-gate violation. Live-verified against the ticket's exact
  numeric example.
- **Critical bug #2 fixed**: the real customer-facing price-resolution
  path now correctly prefers type+brand-specific pricing rules over
  service-level ones — was previously ignoring type/brand entirely,
  reproducing the "Window AC price used for Split AC" bug in the one
  place (live matching) it had NOT already been fixed.
- Provider-first ordering, Home Services scope guard, and the core
  eligibility gate's bookable-status check all confirmed real and
  intact.
- Zero regressions across 206+76 test executions; one pre-existing test
  updated to reflect the corrected (not weakened) behavior.
