# Playwright Baseline — Round 2 (Workstream 4)

## Status: NOT RUN this round (honest deferral)

Time budget this round was spent on: (a) getting a genuinely clean WSL
install+typecheck+test baseline for all 4 apps (which surfaced 2 real,
previously-undiscovered defects — the missing `@testing-library/dom` dep
and the tenant-portal React version mismatch — both documented), (b)
resolving Super Admin access, (c) role-boundary verification via direct API
calls, and (d) the catalog/pricing continuity re-confirmation. Installing
Playwright browsers (`npx playwright install`) and running/writing actual
browser-driven test flows was not reached.

`@playwright/test` is already a devDependency in `frontend/tenant-portal`
(confirmed present in `package.json`, installed cleanly as part of the
workspace install this round) and a `test:browser` script
(`playwright test`) exists — so the harness is present and installable, it
was simply not exercised this round.

## What this means for the smoke flows requested

Customer login+booking visibility, tenant login+booking visibility,
technician login+assigned-job visibility, role-protected navigation, and
refresh persistence were all instead verified this round via **direct API
calls** (see `role-entry-verification.md` and Round 1's
`live-e2e-evidence.md`), which proves the real backend contract and
cross-app data continuity but does NOT prove the actual browser UI wiring
end-to-end. This is a real, disclosed gap, not a substitute claimed as
equivalent.

Deferred to a later round: `npx playwright install` (browser binary
download), then running the existing `test:browser` suite and/or writing
the specific smoke flows named in the brief.
