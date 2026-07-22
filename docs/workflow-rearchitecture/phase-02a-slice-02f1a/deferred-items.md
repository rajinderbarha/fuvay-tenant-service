# Deferred Items — Slice 2F-1A

## Product decisions (see product-decisions-required.md for full detail)
1. Voluntary tenant self-pause as a distinct feature/permission — not
   decided, not built.
2. True subscription-cancellation capability, distinct from `downgrade_plan`
   — not decided, not built.
3. Whether `tenant_owner` should ever be granted any of the 8
   `PLATFORM_ADMIN_ONLY` permissions — not decided; technical guard is ready
   either way.
4. Suspend/terminate reason-category-based workflow branching (e.g.
   different approval levels for fraud vs. payment-failure) — not decided,
   not built.

## Engineering gaps (discovered, not fixed this slice)
1. `confirm_termination`'s claimed 90-day scheduled tenant-schema deletion
   — no job exists.
2. `request_gdpr_deletion`'s claimed 72-hour anonymization — no execution
   mechanism exists.
3. The `tenant_engine.router` vs `admin_router.py` `/suspend` route
   duplication — not consolidated.

## The core remaining platform-wide work (unchanged in kind from Slice 2F/2F-1)
Extend `require_tenant_mutation_permission` to the remaining ~18 router
modules. This slice did not touch any module besides `tenant_engine.router`
(read-only audit/classification/test work only), per the brief's explicit
"do not begin provider_portal.router" instruction.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, guided workflows, page consolidation, visual
redesign, booking-pipeline work, chat consolidation, `readonly@`
remediation, migration 144 application, granting any new permission to any
role — none touched, consistent with every prior slice.

## Recommended next slice
`provider_portal.router` (24 endpoints), following the same
investigate → classify → apply → test → document pattern, this time
applying the Workstream 1/2 evidence-based classification discipline
(frontend caller evidence, service-implementation reading, no
name-based guessing) from the start rather than as a follow-up correction.
