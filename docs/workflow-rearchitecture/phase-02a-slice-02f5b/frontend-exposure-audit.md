# Frontend Exposure Audit — Workstream 10

## Method
Grepped `frontend/super-admin/lib/api.ts` for all 17 mutation path
fragments (`deposits/*/approve|reject|record-offline|refund|adjust`,
`topups/*/retry-credit|refund`, `warranty-claims/*/assign|request-documents|approve|reject|settle`,
`payouts/*/approve|reject|mark-processing|mark-completed|mark-failed`).

## Result
All 17 client-side API functions exist in `lib/api.ts` (lines 8600-8722)
and call the correct `/v1/admin/finance/*` mutation paths — no drift
between frontend caller and backend route confirmed for any of the 17.

Pages found calling these: `app/admin/finance/deposits/[deposit_id]/page.tsx`,
`app/admin/finance/topups/[topup_id]/page.tsx`,
`app/admin/finance/topups/page.tsx`, `app/admin/finance/payouts/page.tsx`,
`app/admin/finance/payouts/[payout_id]/page.tsx`, `app/admin/finance/page.tsx`.

## Tenant-portal exposure
Zero occurrences of `/v1/admin/finance/` in `frontend/tenant-portal` —
re-confirmed this slice (already established in Slice 2F-5A). No tenant
persona can reach any finance_hub mutation from the frontend, consistent
with the backend authorization finding.

## Role-based UI gating
This slice did **not** perform a per-component, per-role audit of which
buttons render for `admin_readonly` vs `admin_finance` vs `super_admin`
in the super-admin Next.js app (that would require tracing client-side
auth-context/role-gating components across 6 page files, which is a UI
audit, not an authorization-router audit). The authoritative enforcement
point verified this slice is the **backend** permission gate — confirmed
via the direct-authorization test matrix that `admin_readonly` receives
403 on all 17 mutations regardless of what the UI renders. No change was
made to any frontend file this slice (out of scope: "do not redesign
finance UI"). This is disclosed as a limitation in `known-limitations.md`,
not a defect — backend-enforced 403s make any UI-level over-exposure a
cosmetic issue, not a security one.

## Conclusion
No frontend changes made. No frontend-exposure defect found within the
scope actually audited (path/route correctness + tenant-portal
non-exposure). UI-level role-based button gating not independently
verified — logged as a limitation.
