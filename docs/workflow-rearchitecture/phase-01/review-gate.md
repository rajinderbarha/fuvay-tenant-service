# Review Gate

Phase 1 (workflow architecture) is complete. **Do not begin Phase 2 implementation, navigation changes, page modifications, or backend changes until this is reviewed and approved.**

## Summary counts
- **Canonical role count:** 10 (super_admin, tenant_owner, staff, technician, customer, guest, admin_operations, admin_finance, admin_security, admin_readonly). 6 additional roles referenced in UI config are unimplemented placeholders.
- **Workflow count:** 62 (see `workflow-inventory.csv`)
- **Canonical workflow count:** ~50 have a single clear canonical implementation
- **Duplicate workflow count:** ~8 areas with 2+ competing implementations (booking/job, reviews, chat x4, finance x3, setup-templates, customer-flow, brands)
- **Disconnected workflow count:** 1 confirmed fully dead (brands admin/provider routers, never mounted); several `[DEPRECATED_410]` endpoints still reachable but blocked
- **Existing page count:** ~154 super-admin pages, ~84 tenant-owner pages, ~16 staff-web pages, ~9 mobile-staff screens, ~26 mobile-customer screens (+19 legacy nested)
- **Pages to keep:** majority (~70%) per `page-disposition-matrix.csv`
- **Pages to simplify:** ~8 (quote/parts screens, profile screens, ambiguous review page)
- **Pages to merge:** ~15 (duplicate nav entries, overlapping finance/insights pages)
- **Pages to convert into workflows:** ~10 (onboarding steps, provider setup steps)
- **User-facing APIs without workflow coverage:** Parts Request/Approval (no entity exists), onboarding risk scoring
- **UI actions without valid API support:** none confirmed fabricated — all actions in reference workflows map to real endpoints, except Parts approval which is explicitly scoped out
- **Required aggregation endpoints:** 5 (see `aggregation-endpoint-recommendations.md`)
- **Critical backend blockers:** 4 (booking/job model split, dual review stacks, missing Parts entity, chat engine ambiguity) — see `workflow-gaps-and-blockers.md`

## Recommended implementation order
See `workflow-implementation-roadmap.md`: Step 0 decisions → zero-risk cleanup → aggregation endpoints → My Work → simplified nav → guided workflows → booking exception workspace → deferred items.

## What we need from you before Phase 2
1. Decisions on the 5 items in Step 0 of the roadmap.
2. Sign-off on the role→navigation model (`role-navigation-matrix.csv`) and page dispositions (`page-disposition-matrix.csv`).
3. Confirmation that the 3 reference workflows (Business Onboarding, Provider Setup, Booking Exception Resolution) are the right starting set.

Nothing has been changed in the codebase as part of this phase — all 20 documents in `docs/workflow-rearchitecture/phase-01/` are analysis and proposal only.
