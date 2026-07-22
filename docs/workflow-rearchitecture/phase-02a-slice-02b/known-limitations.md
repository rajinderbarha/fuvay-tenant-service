# Known Limitations — Slice 2B

1. **2 confirmed invalid persisted user accounts remain unremediated** (`manager@demo-ac-services.local` = `tenant_manager`, `readonly@demo-ac-services.local` = `tenant_readonly`) — per explicit instruction, only a remediation recommendation was produced, not an executed fix. These accounts currently have zero effective permissions.
2. **`readonly@demo-ac-services.local` has no safe automatic role mapping** — the 10 canonical roles have no "tenant-side read-only" concept. Requires a product decision (see `invalid-role-remediation-recommendation.md`).
3. **Intelligence KB's `allowed_roles_json` is unenforced dead configuration** — presents as an access control to the admin configuring it, but has zero actual effect. Flagged for a future product decision (build real enforcement, or remove the field/UI) — not fixed this slice since it requires a design decision, not a mechanical correction.
4. **Detection query for future invalid-role drift is documented but not automated** — the query in `invalid-role-remediation-recommendation.md` is not wired into CI or a scheduled check; running it is a manual action today.
5. **Tenant-owner and staff/manager full shell remaps remain deferred** (unchanged from Slice 2) — this slice added breadcrumbs to the existing shells but did not restructure their navigation groupings.
6. **`useBreadcrumbOverride()` was wired into exactly 1 tenant-portal page** — the mechanism is reusable, but no other contextual page (e.g. `/customers/[id]`, `/(tenant)/service-jobs/[id]/quotes`) was updated to use it this slice.
7. **`/staff/jobs` vs `/staff/home-services/jobs` duplicate remains unconsolidated** (unchanged from Slice 1's finding).
8. **No frontend automated test coverage for the new breadcrumb behavior** — verified via TypeScript compilation and manual code review only, consistent with the lack of a frontend test runner throughout this workflow-rearchitecture series.
9. **Pre-existing duplicate-operation-ID warnings** in `service_setup/templates_router.py` remain, unrelated, not fixed (same as every prior slice).
