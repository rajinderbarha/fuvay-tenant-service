# Package Definition Lifecycle — Workstream 4

## Model
`ServicePackage` / table `service_packages`. No version field exists —
"cloning" (see below) is the only versioning-like mechanism; there is no
package-history/revision table. This is not invented in this slice.

## Actions and guards

| Action | Precondition | Result | Reversible |
|---|---|---|---|
| `create_package` | none | new row, `is_active` per payload default | delete/deactivate |
| `update_package` | package exists; price/deposit/credit fields validated non-negative; `credit_topup` packages cannot carry a positive `security_deposit_amount`; `plan_level` validated against an allowlist | fields updated in place | yes (further update) |
| `activate_package` | none (idempotent) | `is_active=True` | yes (`deactivate_package`) |
| `deactivate_package` | none (idempotent) | `is_active=False` | yes (`activate_package`) |
| `clone_package` | source package exists | new package + copied `PackageFeature`/`PackageLimit` rows | delete the clone |
| `delete_package` | **blocks if any `TenantPackageAssignment` row references this `package_id`** (pre-existing guard, confirmed correct) | soft-delete (`deleted_at` set, `is_active=False`) | not directly (soft-deleted, not restorable via this router) |
| feature/limit create/update/delete | package exists (feature/limit additionally scoped to the parent `package_id`) | sub-resource CRUD | yes for create/update; delete is a hard delete |

## Verified findings
- **Published/assigned packages cannot be destructively deleted**:
  `delete_package`'s existing-assignment guard (from MODULE-L5-32) was
  re-verified this slice via direct source read — it queries
  `TenantPackageAssignment.package_id == package_id` with no status
  filter, meaning ANY assignment (even a long-expired or rejected one)
  blocks deletion. This is more conservative than strictly necessary but
  is not a defect — it fails toward safety, not toward data loss.
- **Package IDs cannot target disconnected records**: every method calls
  `_load_package(package_id)` first, which raises `NotFoundException` for
  a missing/soft-deleted row (verified via `_load_package` source).
- **Tenant roles cannot create or edit package definitions**: all 13
  routes require a `PACKAGES_*` permission granted to no role but
  `super_admin` — confirmed via the direct-authorization test matrix (all
  5 tenant roles get 403 on all 13).
- **Illegal/repeated transitions fail safely**: `activate_package`/
  `deactivate_package` are simple idempotent boolean toggles — re-invoking
  either has no destructive side effect. No "already active" error is
  raised, which is intentional (not a defect) since re-activating an
  already-active package is harmless.
- **No package versioning was invented.** `clone_package` creates an
  independent new row; it does not link back to the source as a
  "version" of anything.

## Conclusion
No defect found in the package-definition lifecycle. All 13 routes are
`PLATFORM_PACKAGE_ADMIN_MUTATION` (super_admin only via `P.ALL`).
