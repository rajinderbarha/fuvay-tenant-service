# FINAL-L5-03 — Performance-Oriented Code Cleanup Report

## Real, high-confidence fixes this sprint

### 1. Site-wide wasted/failing request on every Tenant Portal page load
`TenantLayout.tsx`'s `SetupWizardDrawer` (unconditionally mounted as part of the layout, not conditionally rendered) fired `tenantSetupApi.getWallet()` → `GET /v1/provider/wallet` on **every single page load across the entire tenant-portal app**, which always failed with an unhandled 500 (dormant `tenant_wallets` table, no row for any seeded tenant). This is a real, structural performance issue matching the mission's "Duplicate API calls" / "Serial API waterfalls" concern class: a guaranteed-to-fail network round-trip on every navigation, adding latency and a masked error to every page. **Fixed**: migrated to `usageCreditsApi.getBalance()`, the already-working canonical endpoint.

### 2. Hydration mismatch forcing full client re-render on Dashboard load
3 instances of `<Skeleton/>` (renders a `<div>`) nested inside `<p>` tags caused React to detect a server/client HTML mismatch and discard-and-rebuild that entire subtree on every Dashboard load — a real, measurable extra render cost beyond the visual bug itself. **Fixed**: changed wrapping elements from `<p>` to `<div>`.

## Checked, not found as issues this sprint
- Unbounded list queries / missing pagination: all `EnterpriseDataGrid`-driven pages (including the 5 migrated this sprint) pass `limit`/`page` params; not found violated.
- Importing complete icon/chart libraries: `lucide-react` (tree-shakeable, per-icon imports confirmed in every file read this sprint — `import { Wrench } from "lucide-react"` style, not `import * as Icons`) and `recharts` (used in exactly 1 file per app per FINAL-L5-00) — no bulk-import anti-pattern found.
- Unstable React keys: the 5 migrated grid pages use `row.id`/`row.job_number`-based keys, not array index.
- Repeated context providers: not found duplicated in the files touched this sprint.

## Not exhaustively re-audited this sprint (real scope limit, stated honestly)
"Oversized client components," "unnecessary client-side rendering," "expensive repeated calculations," "large shared bundle imports," "serial API waterfalls" across the full ~100+ pages per app were not individually profiled — this sprint's performance work was targeted at the two concrete, evidence-backed defects found (dormant-endpoint waterfall, hydration mismatch), not a general performance audit. Per the mission's own text: "Do not claim 90+ Lighthouse here; full performance certification is FINAL-L5-14" — full profiling is explicitly out of this sprint's scope.

## Result
Two real, structural, evidence-backed performance defects found and fixed; broader profiling correctly deferred to the mission's own designated future sprint (L5-14).
