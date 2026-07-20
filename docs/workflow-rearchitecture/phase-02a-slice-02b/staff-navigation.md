# Staff Navigation — Slice 2B

## Scope this slice
Verification only — the distinct 7-item Staff/Manager shell (separate from technician's) remains deferred, as building it requires new Team/Customers/Business pages that don't exist yet in the shared `StaffLayout` shell (explicitly out of scope: "do not implement new workflow pages beyond what is required to make approved existing functionality correctly reachable").

## Verified
- **No invented manager RBAC role** — `useStaffContext.ts`'s gate (`isTechnician = user.role === "technician" || user.role === "staff"`) still only recognizes the 2 real canonical roles; re-confirmed unchanged.
- **`/staff/my-work` remains reachable** — unchanged from Slice 1/2, now also has a breadcrumb (new this slice).
- **Parts Request creation remains contextual to ServiceJob** — unchanged; the technician job detail page still only ever operates on `ServiceJob`.
- **Provider-only Mark Installed does not appear to staff/technician** — re-confirmed by re-reading both `/staff/jobs/[job_id]/page.tsx` (no install button, no install API call) and comparing against `/(tenant)/service-jobs/[id]/execution/page.tsx` (has it, correctly gated to tenant-side users reaching that page).
- **Duplicate job/quote entry points** — `/staff/jobs` vs `/staff/home-services/jobs` remains a known, documented, unresolved duplicate from Slice 2 (not consolidated this slice — consolidating navigation without merging backend models, as the brief requests, was judged the same scale of change as the broader shell remap and deferred alongside it, to avoid inconsistently fixing one duplicate while leaving the tenant-owner shell's larger remap undone).

## Real addition this slice
Breadcrumbs (previously entirely absent from the technician/staff shell — see `breadcrumb-reconciliation.md`).

## Not done this slice (deferred, unchanged from Slice 2)
- Distinct Staff/Manager shell.
- `/staff/jobs` vs `/staff/home-services/jobs` consolidation.
- Team/Customers/Business page visibility permission gating for a future distinct staff shell (no such pages exist yet in this shell to gate).
