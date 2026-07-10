# ADMIN-TENANT-E2E-09B — Frontend Read-Only UX Hardening Report

## What was added

`lib/api.ts` (tenant-portal): `getAccessScope()` decodes the `access_scope` JWT claim
client-side (no extra API call); `isTenantReadOnly()` returns true when
`access_scope === "customer_support_limited"`.

`app/(tenant)/tenant/setup/services/page.tsx` — this is the real, currently-live Home
Services setup wizard (the older `/provider/service-setup` page carries an explicit
"This page has moved" deprecation banner pointing here):
- `ServiceSetupWizard` component computes `const readOnly = isTenantReadOnly();`.
- A "View-only access" banner is shown on the final (pricing/publish) step: *"You can view
  this setup but cannot make changes. Contact an owner or manager to update this
  information."*
- `Save Draft` and `Publish Service` buttons are `disabled={readOnly}`.
- The three step-advance `Next` buttons on the Types/Pricing/Brand-Pricing steps (which each
  perform a real PUT save before advancing) are also `disabled={readOnly}`.

## Scope note (honest)

Given the sprint's time budget, the read-only banner/disabling was applied to the primary,
currently-live setup wizard only. The older `/provider/service-setup` and
`/provider/service-coverage` pages were not touched — they are lower-traffic /
partially-deprecated surfaces. Backend enforcement (Part 2) is unconditional and applies to
all of them regardless of any frontend state, so there is no security gap from this scoping
choice — only a UX-polish gap on the untouched pages (a P2, noted in Remaining Blockers).

## Verification

- `npx tsc --noEmit` in `frontend/tenant-portal`: 0 errors (confirmed after these edits).
- `npm run build`: succeeds, all routes compiled including `/tenant/setup/services`.
- Manual grep confirms no forbidden labels or mock data were introduced (see separate scans).
