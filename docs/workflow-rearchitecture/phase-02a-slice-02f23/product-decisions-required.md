# Product Decisions Required — Slice 2F-23

None of these blocks the selected module. They are refinements surfaced
during investigation.

## 1. May `staff` reply to or flag customer reviews?
The selected module's routes currently admit everyone. The safe default for
2F-24 is `tenant_owner` + `super_admin` (the business voice and moderation
posture). Whether a `staff` member may reply on the business's behalf is a
product call. Widening later is trivial; narrowing after release is not — so
the recommendation is to start narrow.

## 2. Who owns the tenant business profile?
`update_business_profile` currently admits `technician` via
`require_technician`, meaning a field technician can change the company's
legal name, GST number, address and contact details, and drive the
verification workflow. Almost certainly unintended, but changing it is a
policy decision about delegation, not a pure security fix.

## 3. Tenant brand assets vs personal profile photos share one dependency
`media.new_router` uses `require_technician` for both the **tenant's** logo
and shop photo and the **user's own** profile photo. These are different
ownership semantics under one gate. A split is likely correct
(`tenant_owner` for brand assets, staff-level for self-photos) but is a
product decision about who manages brand identity.

## 4. Analytics export and download privacy
`provider_run_report` accepts a client-controlled `filters` dict and an
`export_format`, and can produce downloadable output. Whether exports need
their own retention, download authorization and audit policy is undecided —
this is the same class of question the compliance export worker raised in
2F-20 and remains unresolved there.

## 5. Global vs tenant-specific brands
`brand_provider_router` lets a tenant request brands and map supported brands
to a service. Whether brands are a global catalog or tenant-scoped
determines what parent-child ownership check is even correct. Needed before
`set_supported_brands` can be closed properly.

## 6. Review flag semantics
`flag_review` immediately sets `review.status = "flagged"`. Whether a single
unilateral flag should change public visibility, or whether flagging should
merely queue a moderation request, is a product decision that 2F-24 will need
in order to define legal state transitions. The security fix (ownership +
persona) does not depend on it.

## Carried forward, unchanged

- Package Commerce payment integration (2F-22 #1)
- Duplicate-pending unique index (2F-22 #2, migration-dependent)
- Compliance export worker and deduplication (2F-20)
- The `tenant-readonly-decision.md` conclusion underlying the two stale
  Slice-2D canaries — still unresolved, still deliberately untouched.
