# Slice 2F-11 Implementation Summary

## Scope
Complete authorization, ownership, and lifecycle closure for
`app.engines.execution.real_estate_router` (4 sub-routers: `agent_router`,
`provider_router`, `customer_router`, `admin_router` — 18 mounted routes
total, 11 genuine mutations).

## Architecture finding (Workstream 0)
The module name contains "execution" and the mission explicitly warned
not to assume a full real-estate product vision. Direct source and model
investigation confirms: **this module implements a real-estate LEAD
EXECUTION TRACKER (a CRM-style lead lifecycle), not a property
marketplace.** There is no `Property`, `PropertyListing`, `PropertyUnit`,
`PropertyMedia`, `Viewing`, `Offer`, or any similar model anywhere in the
codebase. The only real-estate-domain model is `RealEstateLead`
(`app/engines/final_records/models.py`), plus two execution-support
models (`RealEstateLeadExecutionEvent`, `RealEstateLeadNote`). Every
capability the mission's extensive workstreams anticipate for property
management, listings, viewings, media, offers, and financial/escrow
behavior is **absent from this codebase** — reported honestly as such
throughout this slice's documentation, not fabricated.

## What was found
`agent_router`'s 11 mutation routes (POST, `/v1/staff/real-estate-leads/*`)
used `get_current_user` only — no role check at all. Any authenticated
user of any role (customer, guest, an unrelated technician, a
cross-tenant staff member) could call every lead-lifecycle mutation
endpoint. The only protection was a pre-existing, correct **object-level**
assignment check inside `RealEstateLeadExecutionService`
(`_assert_agent_owns_lead`, exact `agent_id` match against the lead's
assigned agent) — but this was never paired with a **persona-level**
role gate, matching exactly the class of gap Slices 2F-2/2F-9/2F-9A
found and closed for other provider-facing routers.

`agent_router`'s GET `/timeline`, `provider_router`'s 2 GET routes, and
`customer_router`'s GET `/tracking` were likewise `get_current_user`-only
reads. `admin_router`'s 2 routes were already correctly
`require_super_admin`-gated.

## What changed
1. **`app/engines/execution/real_estate_router.py`**:
   - All 11 `agent_router` mutations now use
     `require_owner_or_office_staff_mutation` (role in {super_admin,
     tenant_owner, staff}, access-scope-aware) — technician deliberately
     excluded, per direct evidence (no mobile/technician caller exists
     anywhere for this module).
   - `agent_router`'s `/timeline` and both `provider_router` reads now
     use `require_staff_or_above` (role check, includes technician,
     no access-scope block — appropriate for a read, not a mutation).
   - `customer_router`'s `/tracking` now uses `require_customer`.
   - `admin_router` is unchanged.
2. **New test file**: `tests/test_phase2f11_real_estate_authorization.py`
   (24 tests) — role-gate HTTP tests for every sub-router persona, plus
   re-verification of the pre-existing, unmodified per-lead assignment
   ownership check.
3. **`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`**
   — 11 rows updated from `UNVERIFIED` to `TENANT_MUTATION_ROLE_SCOPE_AWARE`.
4. **`docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`**
   — `app.engines.execution.real_estate_router` row updated: 0/11 → 11/11
   protected.

## What did NOT change
`RealEstateLeadExecutionService`'s existing, correct
`_assert_agent_owns_lead` assignment check, `LEAD_TRANSITIONS` state
machine, and `_set_status`'s validate-before-mutate ordering were all
already correct and are unmodified. No permission or role was created.
No property/listing/media/offer/viewing capability was built (none
exists to build on — see `real-estate-model-lineage.md`). No frontend
file was modified (no component calls this module's API client at all —
see `frontend-exposure-audit.md`). `execution.coaching_router`,
`field_ops.checklist_router`, `field_ops.staff_router` were not begun.
`readonly@demo-ac-services.local` and migration 144 were untouched.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`. Tenant mutation coverage: **117/182** (up from
106/182 — 11 newly protected, all within the pre-existing denominator;
this module's routes were already counted in that inventory before this
slice, unlike customer-facing routes).
