# Staff and Technician Navigation Implementation

## Existing gate (verified, not changed)
`frontend/tenant-portal/hooks/useStaffContext.ts` already computes `isTechnician = user.role === "technician" || user.role === "staff"` — both real canonical roles, no invented "manager" role anywhere in this gate. `StaffLayout.tsx` blocks any other role before rendering navigation.

## What this slice added
A real-data badge on the "My Work" nav item:
- **Source:** `GET /v1/staff/my-work` (Slice 1 endpoint), no new backend call was added.
- **Count logic:** items where `priority === "urgent"` or `category === "REQUIRES_MY_ACTION"`.
- **Loading behavior:** no badge rendered while the request is in flight.
- **Error behavior:** no badge rendered on failure — never a fake "0". This was verified by code inspection (`if (work.error || work.loading || !work.data) return null`), not just asserted.
- **Zero-but-successful behavior:** if the request succeeds and the count is genuinely 0, no badge renders either (a badge showing "0" is visually indistinguishable from a broken badge and adds no information) — this is a UX choice, not a dishonesty concern, since it's clearly distinguished from the error/loading case at the code level.

## Parts Request scoping (verified unchanged, correct)
- Technician's `/staff/jobs/[job_id]` page only ever operates on `ServiceJob` — confirmed by its API calls (`homeServiceStaffJobsApi`, scoped to `/v1/staff/service-jobs`). No Parts UI could appear for an incompatible record because this page never renders one.
- Technician does **not** see a "Mark Installed" action — confirmed by direct inspection: only the provider/tenant execution page (`/(tenant)/service-jobs/[id]/execution`) has the install button (added Slice 1); the technician job detail page has no such button and no such API call.
- Provider/tenant Mark Installed remains reachable — unchanged from Slice 1, re-verified this slice by reading the file again.

## Not done this slice (deferred)
- A distinct "Staff" (office manager, non-technician) shell separate from the technician shell — per Phase 1A's decision, staff and technician currently share this same shell, permission-filtered. Building a genuinely distinct 7-item Staff grouping (Home, My Work, Jobs, Team, Inspection and Quotes, Customers, Business) as specified in the brief would require new pages (Team, Customers, Business views for office staff) that don't exist yet in this shell — that's new page-building, out of scope for a navigation-reconciliation-only slice ("do not implement new workflow pages beyond what is required to make approved existing functionality correctly reachable").
- Technician's own target grouping (Today, My Work, My Jobs, Inspection and Quote, Work Completion, Profile) vs. the current shell's actual labels (Dashboard, My Work, My Profile, Skills & Services, Service Areas, Availability, Assigned Work, Messages, Documents, Notifications, Activity, Security/Sessions) were not remapped/relabeled or consolidated into tabs this slice — that is page-consolidation-scale work (Workstream 8/9 territory), explicitly deferred alongside the tenant-owner shell remap.
