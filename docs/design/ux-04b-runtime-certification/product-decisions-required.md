# Product Decisions Required (UX-04B)

Carries forward all UX-04A items (unchanged; item 7's ServiceBooking
fixture-type question is now partially addressed by the new
`SourceBookingReference`/`JobProvenance` types, but the underlying
provisional-id limitation remains open), plus:

10. **App-wide color-contrast tokens** (`--text-secondary`,
    `--warning-text` in light mode) — found by this pass's real axe-core
    scan, fall short of WCAG AA 4.5:1. Affects ~130 pre-existing routes
    across the whole tenant-portal app, not just UX-04. Needs a
    design-governed decision on new token values and a dedicated pass to
    apply them app-wide (not a narrow correction-pass change). See
    `accessibility-test-report.md`.
11. **Stray nested `package-lock.json` files** (`frontend/tenant-portal`,
    `frontend/super-admin`) — pre-existing since the original repo
    baseline. This pass worked around their effect on `frontend/tenant-portal`
    by pinning the exact react version, but the lockfiles themselves are
    still present and could cause a similar defect for a different
    package pin in the future. A dedicated toolchain-hygiene pass should
    delete them and confirm npm workspaces installs correctly without
    them (also touches `frontend/super-admin`, out of this phase's edit
    scope).
