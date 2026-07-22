# Package Assignment and Purchase Integrity — Workstream 5

## Canonical service method
`PackageCommerceService.create_package_assignment(tenant_id, package_id, payment_reference=None, is_paid=False)`
writes to `TenantPackageAssignment` / table `tenant_package_assignments`.
Re-verified against the current repository (not merely carried over from
Slice 2F-5A):

- Loads the package via `_load_package` and requires `pkg.is_active`
  (raises `PACKAGE_INACTIVE` otherwise) — an unpublished/inactive package
  cannot be assigned.
- **Price is server-derived**: `price_amount=pkg.package_price` is read
  from the loaded `ServicePackage` row — the caller has no `price`
  parameter at all in this method's signature, so client-supplied price
  cannot override canonical pricing by construction (not merely by
  validation).
- **Duplicate-assignment guard** (MODULE-L5-30, re-confirmed unmodified):
  queries for an existing assignment in
  `{"selected", "pending_review", "pending_payment", "paid_pending_approval"}`
  for the same `tenant_id` + `package_id` and raises
  `PACKAGE_ALREADY_PENDING` if found — one in-flight selection per
  tenant+package.
- `starts_at`/`expires_at` remain `NULL` until a separate admin-approval
  step (`activate_tenant_package_assignment`) runs — assignment creation
  alone does not activate service.

## Callers (re-verified this slice)

| Caller | Route | Persona | `is_paid` | Notes |
|---|---|---|---|---|
| `package_commerce.admin_router.admin_purchase_package` | `POST /v1/admin/tenants/{tenant_id}/packages/{package_id}/purchase` | super_admin only (`PACKAGES_CREATE`) | `True` (admin recording as paid) | `tenant_id` sourced from the URL path (admin explicitly targets a tenant — not client-supplied in a way that could target another tenant on the caller's own behalf, since the caller here IS the platform admin) |
| `package_commerce.tenant_router.tenant_purchase_package` | tenant-facing route (not in this module's scope) | tenant_owner (their own tenant only) | `False` initially (paid via a separate flow) | `tenant_id` is the tenant's own authenticated tenant context — confirmed via a source read that this route does not accept an arbitrary tenant_id parameter, so a tenant cannot assign a package to another tenant |

Both callers converge on the identical canonical service method and its
guards (inactive-package rejection, duplicate-pending rejection,
server-derived price) — **not merged into one route**, since they are
intentional, persona-specific entry points (admin recording on a
tenant's behalf vs. tenant self-service), consistent with the mission's
instruction not to merge them.

## Verified findings
- Tenant cannot assign a package to another tenant (tenant_router's
  caller has no foreign-tenant_id parameter).
- Tenant cannot select an inactive/unpublished package (`PACKAGE_INACTIVE`
  guard, shared by both callers via the canonical service).
- Client-supplied price cannot override canonical pricing (no price
  parameter exists on the method signature at all).
- Duplicate assignments do not double-charge or double-credit: the
  pending-status guard blocks a second in-flight assignment; and no
  credit is granted at assignment time at all ("Wallet credits are NOT
  added here" per the method's own docstring) — credits are only granted
  on a later, separate admin-approval step, out of this method's blast
  radius.
- Retry behavior is safe: a retried purchase call for the same
  tenant+package either succeeds once (first call) or raises
  `PACKAGE_ALREADY_PENDING` (subsequent calls) — no silent double-write.

## Not re-litigated
`activate_tenant_package_assignment` / `reject_tenant_package_assignment`
(the admin-approval step downstream of assignment creation) were read for
context but their own state machine was not the focus of this slice's
mission (Workstream 5 scopes "package assignment and purchase," which is
the *creation* step) — no defect was found or claimed in that downstream
step either, but it was not exhaustively tested here.
