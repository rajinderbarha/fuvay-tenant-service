# Financial Model and Ledger Lineage — Workstream 4

## package_commerce.admin_router
- **Package/PackageFeature/PackageLimit**: platform-wide catalog rows, no
  tenant key — package definition is not tenant-scoped by design (a
  package is a sellable plan definition, not a tenant record).
- **TenantPackageAssignment**: tenant_id + package_id keyed, created by
  `PackageCommerceService.create_package_assignment` — the single
  canonical method for BOTH admin-recorded and tenant self-service
  purchases (confirmed, see `finance-capability-ownership-matrix.csv`).
- **TenantWallet** (via `UsageCreditService`, not touched directly by this
  router): tenant_id-keyed; `admin_topup_wallet`/`admin_adjust_wallet`
  delegate entirely to `UsageCreditService`, which is out of this slice's
  direct-inspection scope (not re-audited) but confirmed to be the
  canonical service (per the FINAL-L5-05J code comment documenting the
  prior fix from direct `TenantWallet` mutation to this canonical service).
- **Commission** (`admin_calculate_commission`/`admin_deduct_commission`):
  operates on a `ServiceJob`/commission ledger — internals not traced this
  slice (out of narrow scope; both endpoints are `require_super_admin`-gated
  regardless of internal correctness).
- **Security deposit endpoints**: confirmed dead stubs (`HTTPException(410)`
  unconditionally) — no model touched at all.

## finance_hub.admin_router
- **SecurityDeposit**: deposit_id-keyed; `adjust_deposit`/`approve_deposit`/
  `record_offline_deposit`/`refund_deposit`/`reject_deposit` all operate on
  this model via a shared `_svc` dependency (not traced to its exact
  tenant-scoping mechanism this slice — flagged in `known-limitations.md`).
- **Payout**: payout_id-keyed; `approve_payout`/`mark_completed`/
  `mark_failed`/`mark_processing`/`reject_payout`.
- **WarrantyClaim**: claim_id-keyed; `approve_claim`/`assign_reviewer`/
  `reject_claim`/`request_documents`/`settle_claim`.
- **TopUp**: topup_id-keyed; `refund_topup`/`retry_credit`.

## Do the two modules mutate the same tables?
**No overlap found** for live, reachable writes. The only apparent overlap
(security deposit) is resolved: `package_commerce.admin_router`'s 3
deposit endpoints are confirmed dead (`DEPRECATED_410`), explicitly
pointing callers to `finance_hub.admin_router` as the canonical owner (per
the code's own docstring). No parallel ledger, no adapter, no
compatibility-read pattern was found between the two modules.

## Not traced this slice
The internal implementation of `finance_hub`'s `_svc` dependency (which
model fields it reads/writes, its exact tenant-scoping mechanism) and
`UsageCreditService`'s full internals were not re-audited line-by-line —
flagged in `known-limitations.md`, not assumed safe or unsafe.
