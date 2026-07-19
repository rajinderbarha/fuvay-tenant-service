# UX-01 Unverified Gates (carried forward)

UX-01 ended `FRONTEND_BUILD_BLOCKED`: typecheck, vitest, and `next build` were never run to
completion for the design-system package or super-admin app — only static source review.
UX-02 hit the identical `npm install` failure on step 0 (see `execution-mode.md`) and therefore
inherits the same unverified gates, now also covering the new UX-02 source:

- `tsc --noEmit` for `frontend/packages/design-system` and `frontend/super-admin` — NOT RUN.
- `vitest run` for design-system `__tests__` and the new `frontend/super-admin/__tests__/ux02/*` — NOT RUN.
- `next build` for `frontend/super-admin` — NOT RUN.
- `next build` non-regression check for `frontend/tenant-portal` (shares design-system) — NOT RUN.

None of these gates should be reported as passing until run on a machine without the
OpenSSL/EPERM npm install failure. See `build-report.md` and `environment-blocker-report.md`.
