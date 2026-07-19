# Approval Gate

This phase (UX-03) is **source-level foundation work, not production-ready
UI**. Before anything here reaches real tenants:

1. A working npm/Node environment must run `tsc`, `vitest`, and
   `next build` clean (see build-command-manifest.md /
   environment-blocker-report.md).
2. Every `product-decisions-required.md` item needs an actual product
   decision.
3. Every `API_CONTRACT_REQUIRED` / `SECURITY_CONTRACT_PENDING` row in
   readiness-state-registry.csv needs a confirmed backend contract before
   its corresponding action goes live.
4. Route consolidation (tenant-route-duplication-map.csv) should happen
   deliberately, with redirects, not by silent page replacement.
5. Super Admin and backend non-regression must be re-confirmed against
   whatever HEAD this branch merges onto (this phase confirms it against
   base commit 8953a84 only).

Until then, treat every artifact under `frontend/tenant-portal/**/ux03/**`
and `app/dev/ux-03/**` as internal design/engineering reference material.
