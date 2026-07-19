# Existing UI Audit (Design Debt)

Observed while building the shared foundation — not fixed in this pass
(would require touching many existing feature pages, out of scope for a
foundation phase):

| Issue | Where observed | Risk |
|---|---|---|
| Raw hex colors inline in many page components instead of CSS vars | both apps, various `app/**/page.tsx` | breaks dark theme parity as pages are touched |
| No centralized status→tone mapping; each page hand-rolls badge colors | both apps | inconsistent status colors across surfaces (a "pending" badge looks different per page) |
| `--card-bg`/`--text`/`--muted-text` aliases had to be back-filled in `globals.css` in a prior fix (see commit history) — sign that token naming isn't consistently referenced | super-admin `globals.css` | future components risk relying on undefined vars again |
| No shared Button/Input/Modal — every page implements its own | both apps | inconsistent focus states, spacing, hover treatment |
| No focus-trap on existing custom modals (spot-checked 2) | super-admin `components/shared` | keyboard users can tab out of open dialogs |
| No `prefers-reduced-motion` handling anywhere pre-existing | both apps | motion-sensitive users get full animation regardless of OS setting |
| No automated tests of any kind | both apps | regressions in shared UI go undetected until manual QA |

## Recommendation
Adopt `@serviceos/design-system` components incrementally as pages are
touched for other work, rather than a big-bang rewrite — see
`design-governance-rules.md` for the "no new raw colors / no new status
outside the registry" rule going forward.
