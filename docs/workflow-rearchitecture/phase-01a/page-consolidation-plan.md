# Decision 7 — Page Consolidation Plan

Target: fewer user decisions and less navigation, not fewer backend capabilities. Every page below keeps its underlying functionality; only its container/route changes.

## Business 360 (tenant_owner + super_admin views)
**Consolidates:** profile, verification/onboarding-status, services (summary), team (summary), finance (summary), compliance/documents.
**Pattern:** Standard Pattern 4 (360-degree detail page) with tabs: Overview | Services | Team | Finance | Compliance | History.
**Full management for each area stays as its own workspace** — the Business 360 tab is a summary + link out, not a re-implementation. (E.g. the Services tab links to the full Services workspace, it doesn't duplicate the pricing editor inline.)

## Business Approval Workspace (super_admin)
**Consolidates:** `/admin/tenants/onboarding` + `/admin/onboarding/providers` (Phase 1 flagged these as likely duplicate).
**Pattern:** Standard Pattern 6 (approval workspace) — one workspace, one list, one detail-approval screen. Whichever of the two pages has the more complete/accurate implementation becomes canonical; the other's route becomes a redirect (RETIRE disposition, not deletion of underlying capability).

## Finance Home (super_admin)
**Consolidates:** finance (home) + usage-credits + deposits + topups + claims + payouts + service-invoices + provider-wallets + commission-records + financial-events — 10 pages.
**Pattern:** Standard Pattern 9-adjacent — one Finance Hub landing with capability tabs, per `finance-capability-ownership.csv`. Deposits tab shows a "temporarily unavailable" state if Decision on security deposit replacement remains unresolved at implementation time (do not silently drop the tab).

## Job Workflow (all roles touching a job)
**Consolidates:** technician's separate Inspection/Quote/Completion pages become tabs of one Job Detail workspace (unaffected by the booking/job decision — these operate on `ServiceJob` only).
**Tenant_owner's jobs/bookings/appointments/service-jobs pages do NOT merge into one list in Phase 2.** Verification confirmed `/v1/bookings`, `/v1/jobs` (field_ops), and `/v1/service-jobs` (ServiceJob) are all three actively used by real, currently-shipped screens — this is not dead legacy weight to quietly drop. They ship in Phase 2 as clearly labeled sub-tabs of one "Jobs" container (cosmetic grouping only, zero data-model change), with a true single unified list deferred until the backend read-aggregation BFF from `booking-job-canonical-decision.md` exists.
**Pattern:** Standard Pattern 4 for detail (ServiceJob only), Standard Pattern 3 for each labeled sub-tab list (unchanged data sources).

## Reporting (both super_admin and tenant_owner)
**Consolidates:** analytics + reports + intelligence + marketing (super_admin, 4→1) and analytics + reports + insights (tenant_owner, 3→1).
**Pattern:** one Reports page with saved-view tabs/filters rather than separate routes per report type.

## Setup Wizard (tenant_owner)
**Consolidates:** profile(business fields) + provider/service-areas + tenant/setup/services + provider/service-coverage + tenant/setup/availability → one guided wizard (Standard Pattern 5), per provider-setup-final-contract.md.
**provider/pricing stays a DETAIL_TAB / advanced page** reachable after initial publish, not a wizard step re-run every time.

## Governance Console (super_admin)
**Consolidates:** security + users + users/roles + users/permissions + audit-logs + engines + workflow-templates + compliance (moved from Finance).
**Pattern:** one Governance landing with tabs; Roles/Permissions tabs explicitly show "not implemented" honesty banner where mutation isn't wired (already true today per Phase 1 finding — preserve, don't hide).

## Staff Profile (technician, web)
**Consolidates:** staff/profile + staff/skills + staff/service-areas + staff/availability (DETAIL_TAB); staff/documents + staff/security/sessions + staff/activity + staff/notifications (ADVANCED_SETTINGS, lower frequency).

## Duplicate nav entries retired outright (no consolidation needed, just pick one)
- tenant-portal: `/reviews` vs `/provider/reviews` → keep `/reviews`
- tenant-portal: `/marketing` vs `/provider/marketing` → keep `/marketing`
- tenant-portal: `/chat` vs `/provider/chat` → keep `/chat` (pending Decision 4 chat domain finalization)
- tenant-portal staff: `/staff/jobs` vs `/staff/home-services/jobs` → keep `/staff/jobs`, confirmed duplicate per Phase 1 frontend audit

## Rule applied throughout
Per approved product direction #8 ("KEEP" ≠ preserve exact route/menu/journey), every consolidation above changes only the container (tab vs standalone page vs drawer) and the primary nav entry point — the underlying API calls, permissions, and data remain unchanged. See `final-page-disposition-matrix.csv` for the page-by-page disposition.
