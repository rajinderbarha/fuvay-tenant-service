# Deferred Items — Slice 2F-1

## The core remaining work (unchanged in kind from Slice 2F, one module closer)
Extend `require_tenant_mutation_permission` (or an equivalent) to the
remaining ~18 router modules Slice 2F's inventory identified as tenant-facing
and unprotected. Recommended next, per Slice 2F's own priority order:
1. `provider_portal.router` (24 endpoints) — team-members/availability/offerings.
2. `execution.home_service_router` (20 endpoints) — but only after resolving
   the alternate-route overlap with `home_service_assignment` first (still
   unresolved, see below).

## Smaller, scoped follow-ups
1. ~~Grant `tenant:suspend`/`tenant:reinstate`/`tenant:terminate`/
   `tenant:plan:manage`/`tenant:data:delete` to `tenant_owner`'s role bundle~~
   — **RESOLVED (Slice 2F-1A): not granted.** Evidence (frontend-exposure
   audit) showed these 8 endpoints are called exclusively by the
   super-admin app; classification corrected from `TENANT_OWNER_MUTATION` to
   `PLATFORM_ADMIN_ONLY`. See
   `docs/workflow-rearchitecture/phase-02a-slice-02f1a/` for the full policy
   closure, `sensitive-capability-policy.md` for the per-capability analysis,
   and `product-decisions-required.md` for the still-open product questions
   (voluntary pause, subscription cancellation, the missing 90-day
   termination-deletion job, the missing GDPR-erasure execution mechanism).
2. **Resolve the `execution.home_service_router` vs
   `home_service_assignment.staff_router`/`provider_router` overlap** —
   unchanged from Slice 2F, still not re-adjudicated.
3. Individually verify the remaining `UNVERIFIED_NO_GUARD` /
   `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` routes across the other 23
   modules for real in-handler ownership checks vs. genuine gaps (Slice 2F's
   83-route finding, still not resolved outside `tenant_engine.router`).
4. ~~Extend the representative-sample HTTP proof (owner-success,
   cross-tenant-reject) from 4 to all 19 endpoints in this module~~ —
   **RESOLVED (Slice 2F-1A):** all 19 now have direct HTTP proof for
   read-only-denial, owner-outcome, and cross-tenant-outcome; the 8
   platform-only endpoints additionally have a direct super_admin-retains-
   access proof. See `endpoint-authorization-test-matrix.csv` in the
   Slice 2F-1A docs.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, guided workflows, page consolidation, visual
redesign, booking-pipeline work, chat consolidation, `readonly@` remediation,
migration 144 application — none touched, consistent with every prior slice.

## Recommended next slice
A single, bounded guard-application pass on `provider_portal.router` (24
endpoints, the next-largest module per Slice 2F's own recommended order),
following the exact same investigate → classify → apply → test → document
pattern this slice used, ending with its own module-scoped
`--verify-module` exit-0 proof before moving on.
