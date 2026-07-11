# FINAL-L5-03 — Shared UI Component Audit

Each of the 3 apps has its own `components/shared/ui.tsx` with a near-identical component family (independently maintained, not a shared package). Building on FINAL-L5-00's sampled dead-code findings (re-verified relevant, not re-run from scratch) plus this sprint's own checks:

| Component family | super-admin | tenant-portal | customer-app | Decision |
|---|---|---|---|---|
| Buttons (`Btn`, `AddBtn`, `EditBtn`, `DeleteBtn`, `ViewBtn`, `MoreBtn`) | `EditBtn`/`DeleteBtn`/`ViewBtn`/`MoreBtn` have **0 consumers** (FINAL-L5-00) | `MoreBtn` has 0 consumers; `EditBtn`/`DeleteBtn`/`ViewBtn` are used | small app, no equivalent needed | **KEEP_SPECIALIZED** per-app; **DELETE_CONFIRMED** candidates for the specific 0-consumer symbols noted (not deleted this sprint — see Dead Code Cleanup Report for why) |
| Data table (`DataTable`) | 31 consumers | **0 consumers** — superseded by `EnterpriseDataGrid` | N/A | **DEPRECATE** the tenant-portal copy (dead), **KEEP** super-admin's (real usage) — genuinely different states per app, not a bug |
| `EnterpriseDataGrid` | Canonical, used by all Enterprise-pattern pages | Same component, separate copy | N/A | **CANONICAL** within each app; cross-app merge not attempted (would require a shared package, out of scope) |
| `Pagination` | 14 consumers | 1 consumer | N/A | **KEEP** both — real usage in both, `EnterpriseDataGrid` has its own internal `EnterprisePagination` for grid pages |
| `SectionHeader` | 83 consumers | 22 consumers | N/A | **CANONICAL**, core primitive in both apps |
| `EmptyState` | 17 consumers | 18 consumers | N/A | **CANONICAL** |
| `Skeleton` | Used, and now has a documented HTML-nesting caveat (see Loading/Empty State Report) | Same, 3 real bugs found and fixed this sprint | N/A | **CANONICAL**, with the nesting caveat now called out in this report for future authors |
| `HealthMeter` | 1 consumer | 3 consumers | N/A | **KEEP** |
| `JobStatusBadge` | 3 consumers | 5 consumers | N/A | **KEEP** |
| `Modal` | Used app-wide | Used app-wide | N/A | **KEEP_SPECIALIZED** per-app |
| Toast/`Toaster` | Present | Present (`TenantLayout.tsx`) | Simpler `ErrorBanner` only | **KEEP_SPECIALIZED** |

## Decision rationale for not merging into one shared package
Per rule 1 and the mission's own "do not force specialized workflows into one generic component if usability suffers" — merging 3 independently-evolved `ui.tsx` files into a shared package is a real, valuable, but **large, cross-cutting infrastructure change** (would require a monorepo workspace/package-manager change, touching every import statement across 3 apps, with no existing test harness to catch regressions from a mechanical merge). This sprint's evidence (0-consumer components differing per app, `DataTable` genuinely dead in one app but heavily used in the other) shows the 3 copies have **already diverged in real usage**, not just accidentally duplicated — consolidating them now would require reconciling those divergences carefully, which is out of this sprint's safe-cleanup scope. Flagged as a real, substantial recommendation in the Deprecation Register for a dedicated future sprint.

Machine-readable version: `shared-ui-component-inventory.json`.

## Result
No `NOT_READY_FINAL_L5_03_SHARED_UI_FAILED` — duplication is real but was already documented (FINAL-L5-00), and the components found dead-in-one-app are recommended for removal (not yet removed, see Dead Code Cleanup Report) rather than the audit being incomplete.
