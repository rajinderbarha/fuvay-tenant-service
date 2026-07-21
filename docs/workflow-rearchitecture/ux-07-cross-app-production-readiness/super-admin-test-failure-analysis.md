# Super Admin Test Failure Analysis — Round 4, Pass 1

## Reproduction

Reproduced from a genuinely clean install: `rm -rf` a prior WSL working
copy, fresh `~/serviceos-ux07-pass1/` created by copying the workspace
root `package.json` + `frontend/packages/design-system` +
`frontend/super-admin` from `G:\serviceos-ux07-cross-app` (HEAD
`b879e93`), then `npm install --workspaces --include-workspace-root
--legacy-peer-deps --no-audit --no-fund`.

`cd frontend/super-admin && npx vitest run` (no lockfile existed at the
workspace root before this install; nothing else was pinned or changed):

```
Test Files  1 failed | 3 passed (4)
     Tests  3 failed | 10 passed (13)
```

This exactly matches the Round 2/3-reported baseline (10/13 passing, 3
failing) — confirming no drift since Round 2.

## Failure 1 & 2 — `RoleDashboard` (both tests in that describe block)

**Test file**: `__tests__/ux02/patterns.test.tsx`
**Component under test**: `components/ux02/widgets/RoleDashboard.tsx`

**Observed error**:
```
ReferenceError: ResizeObserver is not defined
  at ../../node_modules/recharts/lib/component/ResponsiveContainer.js:101:20
```

**Root cause**: `RoleDashboard` renders finance/risk-overview widgets that
use recharts' `<ResponsiveContainer>`, which calls the browser's
`ResizeObserver` API on mount to track its container's size.
`frontend/super-admin/test-setup.ts` only imported
`@testing-library/jest-dom/vitest` — it never registered a
`ResizeObserver` polyfill/mock for the jsdom test environment. jsdom
itself does not implement `ResizeObserver` (it's a real-browser-only API),
so any test that renders a component containing `<ResponsiveContainer>`
throws immediately.

**Classification: test-infrastructure bug** (missing browser API mock).
Not a stale expectation (the widgets' finance/risk gating logic the test
actually asserts is unaffected) and not a source defect (the real browser
that runs `frontend/super-admin` in production always provides
`ResizeObserver` — this only breaks inside jsdom).

**Fix**: added a minimal `ResizeObserver` mock (`observe`, `unobserve`,
`disconnect` as no-ops) to `test-setup.ts`, registered only if
`globalThis.ResizeObserver` is undefined. No test assertions were
weakened, retried, or skipped — after the mock, `RoleDashboard`'s finance-
widget-visibility and risk-overview-visibility assertions were unchanged
and both passed on the first try.

## Failure 3 — `EnterpriseDetailPage` "switches sections via the nav buttons"

**Test file**: `__tests__/ux02/patterns.test.tsx`
**Component under test**:
`components/ux02/patterns/EnterpriseDetailPage.tsx`

**Observed error**:
```
TestingLibraryElementError: Found multiple elements with the text: Section B
  <option value="b">Section B</option>
  <button ...>Section B</button>
```

**Root cause**: `EnterpriseDetailPage` is a responsive pattern used by
Tenant 360 and Compliance Case Detail. It intentionally renders a sticky
desktop `<nav>` of `<button>`s AND a mobile `<select>` of `<option>`s for
the same section list, toggling their visibility via a scoped
`@media (max-width: 768px)` CSS rule (`.ux02-desktop-only` /
`.ux02-mobile-only`), not via conditional rendering. jsdom does not
evaluate CSS media queries, so in the test environment both the button
and the option carrying the text "Section B" are simultaneously present
and "visible" from Testing Library's perspective. The test's
`screen.getByText("Section B")` matches by visible text across any
element type and is therefore ambiguous — it was never scoped to the
`<nav>`/button specifically.

**Classification: test-infrastructure bug** (ambiguous query caused by a
jsdom limitation — CSS media queries aren't evaluated — combined with a
query that wasn't scoped tightly enough). Not a source defect:
`EnterpriseDetailPage.tsx` behaves correctly in a real browser, where only
one of the two elements is actually visible/interactive at a time per the
media query. Not a stale expectation: the test's intent (verify clicking
a nav item switches the active section) is still correct and unchanged.

**Fix**: changed
`fireEvent.click(screen.getByText("Section B"))` to
`fireEvent.click(screen.getByRole("button", { name: "Section B" }))` —
this selects only the `<button>` (the `<option>` has no `button` role),
eliminating the ambiguity without touching `EnterpriseDetailPage.tsx` or
weakening what the test verifies.

## Result

All 3 fixes are test-infrastructure-only (2 files changed:
`test-setup.ts`, `patterns.test.tsx`). No test was skipped, no retry/
timeout inflation was added, no assertion was weakened, and no React
version pin was touched. 13/13 passing after the fix — see
`super-admin-test-report.md` and `repeated-test-stability.md`.
