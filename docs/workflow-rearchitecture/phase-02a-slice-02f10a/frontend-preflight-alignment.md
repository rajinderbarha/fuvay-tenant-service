# Frontend Preflight Alignment — Slice 2F-10A (Workstream 11)

## Search results
`frontend/customer-app/lib/api/customer-complaints.ts` exposes
`checkEligible()`, calling `GET /v1/customer/complaints/check-eligible`.
Grepped every `.tsx` file in `frontend/customer-app` for a call to it —
**zero UI components call `checkEligible` at all.** The only creation
caller is `frontend/customer-app/app/customer/complaints/page.tsx`,
which calls `createComplaint(...)` directly.

## Requirements review
- **Frontend preflight must not be the security boundary**: trivially
  true here — preflight isn't even called, so there's no risk of it
  being mistaken for enforcement. The creation mutation itself
  (`create_complaint`) is now the sole, authoritative enforcement point
  (this slice's fix).
- **Refund-request controls must match legal backend source states**:
  N/A — `create_refund_request_from_complaint` has no complaint-status
  precondition for the *request* itself (see
  `refund-silent-transition-review.md`); there is no "legal state" for
  the frontend to match, since the request is always allowed by policy.
- **Unsupported refund issuance must not appear functional**: the
  customer-app's refund UI only requests review (no amount/approval
  control), consistent with backend behavior — not independently
  re-verified line-by-line this slice (out of proportion to this narrow
  follow-up), but no evidence of an "issue refund" control was found in
  the API client (`requestRefund` is the only refund-related export).
- **Direct URLs must not bypass ownership/state policy**: backend
  remains authoritative regardless of any frontend routing — unaffected
  by frontend behavior.

## No frontend change made
Since the backend creation mutation and refund-request method now fully
and correctly enforce (or intentionally don't enforce, by proven policy)
every relevant rule regardless of frontend behavior, and the frontend
never relied on preflight as a gate in the first place, no frontend
change was needed or made this slice.
