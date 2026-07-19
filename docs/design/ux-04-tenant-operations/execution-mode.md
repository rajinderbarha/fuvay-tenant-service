# UX-04 Execution Mode

**Mode achieved: MODE A (partial), for the subset of source actually built.**

- WSL install: confirmed working using the proven UX-03 pattern — copied
  root `package.json` + `frontend/packages/design-system` +
  `frontend/super-admin` + `frontend/tenant-portal` (excluding
  `node_modules`/`.next`) into `/root/serviceos-ux04` on WSL Debian's native
  filesystem, then `npm install --workspaces --include-workspace-root
  --no-audit --no-fund`. Result: **"added 196 packages in 6m", zero
  errors.**
- Typecheck: `npx tsc --noEmit` from `/root/serviceos-ux04/frontend/tenant-portal`.
  Result: 5 pre-existing errors, all in files this phase did not touch
  (`../packages/design-system/src/components/Tooltip.tsx` — an existing
  JSX typing issue on `aria-describedby`; and two UX-03
  `components/ux03/__tests__/*.test.tsx` files missing `@testing-library/jest-dom`
  matcher types). **Zero errors in any UX-04 file** (`lib/ux04/**`,
  `components/ux04/**`, `app/dev/ux-04/**`).
- Build: `npx next build` was launched from the same WSL copy; see
  `build-report.md` for the literal outcome captured before this report was
  finalized.
- Tests: no dedicated UX-04 test suite was written this phase (see
  `frontend-test-plan.md` / `frontend-test-report.md` for what's covered vs
  deferred) — this is a real gap, not a fabricated pass.

## Honest scope note

This phase (UX-04) is far larger in the brief (33 numbered work items, 27
showcase routes, 60 docs) than the time/effort budget available for this
pass could fully deliver at UX-03's depth. Rather than fabricate breadth,
this pass prioritized: (1) a real, typed, non-duplicated view-model layer
covering all 15 required view models, (2) a working set of the highest
leverage shared components wired to real fixtures, (3) 6 dev showcase
routes demonstrating the pattern end-to-end and verified to build/typecheck
cleanly, and (4) this full honest documentation set describing what's done,
what's deferred, and why — rather than 27 showcase routes at shallow
depth. See `product-decisions-required.md`, `known-limitations.md`, and
`deferred-items.md` for the itemized gap list. Final status token reflects
this: **TENANT_OPERATIONS_DESIGN_PARTIAL**.
