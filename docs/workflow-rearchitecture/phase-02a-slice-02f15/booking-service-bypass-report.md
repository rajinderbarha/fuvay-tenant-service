# Booking Service-Layer Bypass Report

## Methods audited

| Method | Callers | Ownership/Authority Before | After |
|---|---|---|---|
| `create_booking` | `POST /v1/bookings` (only caller) | customer_id unvalidated for non-customer actors; no relationship check | customer_id validated (existence+role+active+non-deleted) + relationship required for non-customer actors (fixed) |
| `confirm_booking` | `POST /v1/bookings/{id}/confirm` (only caller) | `_assert_can_access_booking` (tenant-scoped, correct); customer explicitly denied (correct) | unchanged — already correct |
| `reject_booking` | `POST /v1/bookings/{id}/reject` (only caller) | same as confirm | unchanged — already correct |
| `convert_to_job` | `POST /v1/bookings/{id}/convert-to-job` (only caller) | `_assert_can_access_booking` + `CONFIRMED`-required + duplicate guard (all correct, pre-existing) | unchanged — already correct |
| `_run_legacy_preflight` | called internally by `create_booking` | tenant/commerce/capacity checks (unmodified, out of this slice's customer-authority scope) | unchanged |

## Conclusion

A stronger router-level guard (this slice's `require_tenant_mutation_permission` upgrade) did not
conceal a weaker service-layer caller for `confirm_booking`/`reject_booking`/`convert_to_job` —
their object-ownership checks were already correct. `create_booking` DID have a genuine
service-layer gap (missing customer validation and missing relationship requirement) — fixed
directly in the service method itself, not merely at the router.
