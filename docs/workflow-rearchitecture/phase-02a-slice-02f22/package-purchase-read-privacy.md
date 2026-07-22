# Read and Privacy Audit — Slice 2F-22

## Correction to Slice 2F-21

2F-21's `selected-next-module.md` listed **4** related reads. The router
actually declares **8** GET routes. The four it missed are the financially
sensitive ones: credit wallet, credit ledger, commissions, and storage quota.
Recorded in `documentation-corrections.md`.

## All 8 reads in `tenant_router.py`

| Route | Dependency | Tenant scoping |
|---|---|---|
| `GET /v1/provider/onboarding/package-summary` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/packages/available` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/packages/purchases` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/security-deposit` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/credit-wallet` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/credit-ledger` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/commissions` | `get_current_user` | `_tenant_id(user)` |
| `GET /v1/tenant/storage-quota` | `get_current_user` | `_tenant_id(user)` |

## Verification

- **Tenant isolation** — every read derives its tenant from the JWT via
  `_tenant_id(user)` and passes it as the service filter. None accepts a
  tenant identifier from path, query or body, so cross-tenant read is
  unrepresentable, exactly as for the mutation.
- **Foreign / missing purchase identifiers** — none of these reads take a
  purchase or assignment ID; they are all tenant-scoped collection or summary
  reads. No IDOR surface and no foreign-vs-missing error-equivalence question
  arises.
- **Other-tenant purchase privacy** — structurally enforced by the same
  filter.
- **Payment reference privacy** — post-2F-22 a tenant-created assignment
  carries no `payment_reference_id` at all (the field is rejected on input),
  so there is less to expose than before.
- **Internal gateway metadata** — none is stored on
  `TenantPackageAssignment`; gateway artifacts live in `platform_commerce` /
  `finance_hub` models these reads never touch.
- **Staff / internal notes** — no such field on this model.
- **GET causes no mutation** — confirmed by reading all 8 handler bodies:
  each calls a `get_*` / `list_*` service method and returns; none writes or
  commits. (Checked explicitly because 2F-20 found a state-mutating GET,
  `download_export`, in the compliance module — that pattern does not recur
  here.)

## Read-only tenant access

Reads deliberately remain on `get_current_user`, so a read-only tenant owner
can still *view* packages, wallet and ledger while being denied the purchase
mutation. That asymmetry is the intended outcome of this slice, not an
oversight.

## Not changed

No read dependency was altered. Tightening reads was out of scope; they were
audited and found correctly tenant-scoped.
