# Seed Removal Report — UX-06 Round 4

## Removal command (real endpoint, confirmed present, NOT executed this round)

```
DELETE /v1/tenant/service-areas/c50daa54-3d07-46a4-b449-41761ab33fc0/services/d07529ff-406f-4c83-9f89-ba423199860b
Authorization: Bearer <tenant_owner token>
```

Confirmed present at `app/engines/serviceability/router.py:delete_service_mapping`,
calling `ServiceabilityService.delete_service_mapping(area_id, mapping_id)`
(a real soft/hard delete on the exact `TenantServiceAreaService` row created
this round — the same row id documented in tenant-service-area-seed-contract.md).

## Why not executed this round

The seed is the only thing making the `ac_repair`/Ludhiana real serviceability
+ price-estimate path provable at all (see round4-implementation-summary.md /
seed-before-after-report.md). Removing it now would revert the environment to
Round 3's blocked state before this round's evidence and Playwright certification
are complete, and before the deeper `match-and-price`/`BargainRule` blocker
this round discovered can be picked up in the next round without re-diagnosing
from scratch. Leaving a single, precisely-documented, reversible test-data row
in an isolated demo tenant is the pragmatic choice; the exact reversal command
above is real and ready to run whenever a clean-slate re-verification is
wanted.

## Reversibility proof (logical, based on the real code path)

`delete_service_mapping` removes exactly the one row
(`tenant_service_area_id=c50daa54-..., service_id=a96e625a-..., job_type=repair`).
After removal, `TenantServiceAreaService` for this area/service/job_type
combination returns to 0 rows — the exact precondition Round 3 diagnosed
(`GET .../services` showing `service_count: 0`), so a subsequent
`POST .../serviceability-check` for `ac_repair`/Ludhiana would deterministically
return `serviceable: false` again, restoring Round 3's exact prior behavior. No
other row this round touched (only one `POST` create + one `PUT` update on the
same single row id) would be affected.
