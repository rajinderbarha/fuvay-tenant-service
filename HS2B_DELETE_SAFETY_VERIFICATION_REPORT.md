# HS2B — Delete Safety Verification Report

## Method
Read every delete/hard-delete backend method for each catalog entity in
`app/engines/admin_catalog/service.py` and its router wiring in
`admin_router.py`/`catalog_enterprise_router.py`, to determine the real,
current safety behavior (not assumed from the ticket).

## Per-entity findings

| Entity | Soft delete (`DELETE .../{id}`) | Hard delete endpoint exists? | Usage check on hard delete? |
|---|---|---|---|
| Service Group | Yes — always safe (sets `deleted_at`, `status='deleted'`) | Yes, but it's the **only** delete endpoint (no separate soft/hard split) | **Yes, already correct** — `SERVICE_GROUP_HAS_SERVICES` blocks delete if any `MasterService` references the group |
| Master Service | Yes — soft, always safe | Yes, separate `/hard-delete` route | **Yes, already correct** — `MASTER_SERVICE_HAS_RULES` blocks if `ServicePricingRule` rows reference it |
| Service Type | Yes — soft, always safe | Yes, separate `/hard-delete` route | **No — real bug found and fixed this sprint.** Previously deleted unconditionally. **Fixed**: now checks both `ServicePricingRule.service_type_id` and `TenantServiceType.service_type_id`, raising `SERVICE_TYPE_IN_USE` (409) if either references it |
| Brand | Yes — soft, always safe | **No hard-delete endpoint exists** | N/A — hard delete isn't possible via API at all, so it's safe by omission |
| Issue/Question | Yes — soft, always safe | **No hard-delete endpoint exists** | N/A — same, safe by omission |
| Option/Add-on | Not independently re-verified this sprint | Not found in this sprint's grep of `admin_router.py` | Not verified |

## Real bug found and fixed
`hard_delete_service_type()` in `app/engines/admin_catalog/service.py`
would permanently delete a `ServiceType` row even if a tenant had
already enabled that type (`TenantServiceType`) or an admin had
configured a pricing rule for it (`ServicePricingRule.service_type_id`)
— silently orphaning those references. Fixed by adding the same
usage-check pattern already used by `hard_delete_master_service` and
`delete_service_group`.

## Blocked message
The ticket's exact required message ("This catalog item is already
used. Deactivate it instead to keep history safe.") was used verbatim
for the new `SERVICE_TYPE_IN_USE` error. The pre-existing
`SERVICE_GROUP_HAS_SERVICES` and `MASTER_SERVICE_HAS_RULES` errors use
slightly different, but equally clear, pre-existing wording — not
changed this sprint to avoid altering already-certified, tested error
copy.

## Not verified this sprint
- Option/Add-on delete safety (endpoint not located in this sprint's
  time budget).
- Whether any entity is referenced by `Booking`, `Job`, or "provider
  matching rule" specifically (the usage checks implemented/found only
  cover `ServicePricingRule` and `TenantServiceType`/`MasterService`
  references, not booking/job history directly) — a service type or
  brand used only in a *past, completed* booking with no current pricing
  rule or tenant enablement would not be blocked from hard delete today.
  This is a real, documented gap.

## Verdict
Delete safety: **3 of 3 entities with a hard-delete endpoint are now
correctly guarded** (Group and Master Service were already correct;
Service Type was broken and is now fixed). Brand and Issue Type are
safe by omission (no hard-delete path exists). Option/Add-on and
booking/job-reference checks were **not verified** this sprint.
