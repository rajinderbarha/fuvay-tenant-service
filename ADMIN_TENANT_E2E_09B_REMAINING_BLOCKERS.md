# ADMIN-TENANT-E2E-09B — Remaining Blockers / Scoped Gaps

None of the following block certification of this sprint's in-scope work; listed for honesty
and follow-up planning.

1. **Other tenant routers still use `require_tenant_owner` without the access_scope gate.**
   `app/engines/provider_portal/router.py` (team-members, availability rules, offerings,
   packages/status) and `app/engines/tenant_engine/portal_router.py` contain dozens of
   additional mutation endpoints sharing the identical access_scope-blind pattern that this
   sprint fixed for service-setup/coverage/pricing. Out of this sprint's strict scope
   (explicitly limited to service setup/coverage/pricing/business-profile). Recommend a
   dedicated follow-up RBAC-hardening sprint using the same
   `require_tenant_mutation_permission` helper already built here.
2. **No `business-profile` mutation route currently exists** to apply the same fix to — the
   prior sprint's finding about it may refer to a route that was since removed or never
   shipped. Nothing to fix; flagged as informational only.
3. **Window AC + LG area-coverage row could not be added** due to a real DB unique constraint
   (`uq_tsas_active_mapping` on `tenant_service_area_services(area, service, job_type)`) that
   only allows one active coverage row per (area, service, job_type) — meaning Split AC and
   Window AC (same service, same job_type=repair) cannot both get independent area-coverage
   rows under the current schema. The type+brand were enabled (additive, safe), but the
   area-coverage row itself needs either a schema change (widening the unique constraint to
   include `service_type_id`/`brand_id`) or an app-level redesign — out of this sprint's
   scope (no schema/migration changes were authorized).
4. **Read-only UX hardening (banner + disabled buttons) applied only to the primary, currently
   live `/tenant/setup/services` wizard**, not the older `/provider/service-setup` (already
   deprecated in-app) or `/provider/service-coverage` pages. Backend 403 protects all of them
   regardless; this is a UX-polish gap only (P2).
5. **Dashboard hydration warning** — not independently re-verified this sprint (pre-existing,
   already documented as out-of-scope and `/dashboard`-only by the prior sprint).
6. **Wrong-tenant (cross-tenant) mutation** was not independently re-tested with a second real
   tenant account in this sprint (only Demo AC Services exists in the seeded dev DB) — the
   fix layers on top of existing tenant-scoping in `TenantCatalogService`, which was already
   enforced before this sprint; not re-verified with a live second-tenant curl call.
7. **83 pre-existing pytest failures** (frontend page-content string-match tests, unrelated to
   this sprint's backend files) remain — documented in Test Results, not caused by this
   sprint, out of scope to fix.

None of the above represent a live authorization gap on the endpoints this sprint targeted.
