# FINAL-L5-05U — ADR: Security Deposit Canonical Permission Family

## Decision

`FINANCE_DEPOSITS_*` (`finance:deposits:read/update/approve/refund`,
defined in `app/core/permissions.py`) is the certified canonical Security
Deposit permission family, used by all frontend controls, all backend
endpoints, and all role bundles.

`FINANCE_SECURITY_DEPOSITS_*` (`finance.security_deposits.*`, 8 keys) is
deprecated. The constants remain defined (never deleted) but are removed
from every role bundle and no longer referenced by any active endpoint,
nav item, route guard, or permission-catalog entry.

## Evidence

### 1. Three live implementations were found, not two

Runtime inventory found the Security Deposit domain implemented across
**three** independent, simultaneously-live endpoint families against the
same `SecurityDeposit`/`SecurityDepositTransaction` tables:

| Family | Path | Permission gate | Completeness |
|---|---|---|---|
| `finance_hub.admin_router` | `/v1/admin/finance/deposits*` | `finance:deposits:*` | List/summary/detail/approve/reject/record-offline/refund/adjust. Real `SecurityDepositTransaction` history via `credit_deposit`/`debit_deposit`. Real `platform_audit_logs` audit. |
| `package_commerce.admin_router` | `/v1/admin/tenants/{id}/security-deposit*` | `finance.security_deposits.*` | get/mark-paid/refund/forfeit. **Zero real frontend caller anywhere.** Mutations write `status` directly with no history row and no ledger call — a real transactional-integrity defect. |
| `platform_commerce.router` | `/v1/commerce/tenants/{id}/deposit*` | Mixed: `TENANT_BILLING_READ/MANAGE` (3 read/initiate endpoints) + `require_super_admin` (1 admin-only mutation) | The real tenant self-service payment flow (confirmed live caller in both super-admin and tenant-portal frontends). Uses `credit_deposit`/`debit_deposit` correctly. |

### 2. The exact root cause of FINAL-L5-05O's "frontend vs. mutation
   endpoint" finding

A live audit of `/admin/finance/deposits` (the actual dedicated Security
Deposits admin page) found:

- **Nav item** (`AdminLayout.tsx`): `requiredPermission: "finance.security_deposits.read"`
- **Page-level route guard** (`RequirePermission` wrapping the entire page): `"finance.security_deposits.read"`
- **Page's own action menu** (Approve/Reject/Record-Offline/Refund/Adjust): `perm.has("finance:deposits:approve"/"update"/"refund")`
- **Every backend endpoint the page calls**: `require_permission(P.FINANCE_DEPOSITS_*)`

Three of four checkpoints used the canonical namespace; only the nav item
and page-level guard used the deprecated one. The practical consequence:
**no role could both see the page and successfully use it** without
holding both namespaces simultaneously. FINAL-L5-05O's bounded fix
granted `admin_finance` both namespaces, which worked for Finance Admin
by coincidence, but left the actual namespace inconsistency in place —
`admin_readonly`, which held only the deprecated alias, could see the nav
item and pass the route guard, but the page's own data fetch
(`financeApi.listDeposits()`, gated by canonical `finance:deposits:read`)
would then 403.

### 3. A real, previously-undiscovered cross-tenant vulnerability

Neither `CommerceService` (the class backing `platform_commerce.router`)
nor `require_permission()` (pure RBAC — role→permission mapping only, no
tenant scoping) ever verified that a caller's own tenant matched the
route's `tenant_id` parameter for `get_deposit_status`/`initiate_deposit`/
`get_deposit_transactions`. Since these are gated by `TENANT_BILLING_READ`/
`TENANT_BILLING_MANAGE` — permissions the `tenant_owner` role legitimately
holds for self-service — **any authenticated tenant owner could substitute
another tenant's UUID and read that tenant's Security Deposit status and
transaction history**. Same defect class as the Service Area cross-tenant
bug fixed in FINAL-L5-05Q (URL identifier captured but never verified
against the caller's actual scope). Fixed this sprint (see Part "Cross-
Tenant Fix" below) — out of this ADR's core naming-namespace scope but
directly adjacent and within "Security Deposit ... tenant isolation"
(mission-mandated bounded scope).

## Canonical keys (mission's minimum-operations checklist, mapped to reality)

| Mission's suggested key | Actual canonical key used | Rationale |
|---|---|---|
| `SECURITY_DEPOSITS_READ` | `FINANCE_DEPOSITS_READ` | Existing key already matches meaning exactly (mission: "use existing keys where they already match... do not create new keys unnecessarily") |
| `SECURITY_DEPOSITS_ADJUST` | `FINANCE_DEPOSITS_UPDATE` | Covers `adjust_deposit`, `record_offline_deposit`, and `platform_commerce.admin_adjust_deposit` (all three "increase/decrease within policy" operations) |
| — (approve/reject workflow) | `FINANCE_DEPOSITS_APPROVE` | Real, distinct verification-workflow semantic not in the mission's minimum list but already correctly separated from READ/UPDATE — kept as-is |
| `SECURITY_DEPOSITS_RELEASE` | `FINANCE_DEPOSITS_REFUND` | This codebase does not implement "release" (unlock without money movement) as a distinct workflow from "refund" (`refund_deposit` sets `status="refunded"`, `hold_state="released"` in one operation) — documented here as a scoping decision, not a gap: building a new distinct release-without-refund workflow is a business-logic feature addition, out of this route/permission-reconciliation mission's bounded scope |
| `SECURITY_DEPOSITS_REFUND` | `FINANCE_DEPOSITS_REFUND` | Same key as RELEASE above, per the note directly above |
| `SECURITY_DEPOSITS_REVERSE` | *(not implemented)* | No reversal endpoint exists anywhere in this domain. Mission's own Part 16 framing ("where implemented") and Part 17 ("Reverse appears only for reversible events") anticipate this may not exist — confirmed absent, not silently assumed |
| `SECURITY_DEPOSITS_EXPORT` | `FINANCE_EXPORT` (`finance:hub:export`) | Reuses the existing platform-wide Finance export permission, matching the established codebase-wide convention (the same key already gates Top-up exports, Commission exports, etc. — one export permission per admin console domain, not per sub-resource) |
| `SECURITY_DEPOSITS_SETTINGS_READ`/`MANAGE` | *(not implemented)* | No Security Deposit settings/configuration endpoint exists anywhere (`FINANCE_SECURITY_DEPOSITS_CONFIG_UPDATE` was defined but never wired to any endpoint, confirmed via `git grep` — genuinely dead, not hidden). Building a settings feature is out of this mission's bounded scope ("Do not redesign the broader Finance UI") |

## Rejected alternative: rename everything to `SECURITY_DEPOSITS_*`

Rejected. `FINANCE_DEPOSITS_*` already exists, is already the namespace
used by the richest, most-complete, real-caller-backed implementation
(`finance_hub`), and is already correctly used by 3 of the 4 checkpoints
on the one dedicated Security Deposits admin page. Renaming it would
touch strictly more files (the entire `finance_hub` router/service/tests)
for zero functional benefit, directly contradicting the mission's own
instruction: "Use existing keys where they already match canonical
meaning. Do not create new keys unnecessarily."

## Rejected alternative: keep both namespaces, reconcile only role bundles

Rejected. This was effectively FINAL-L5-05O's approach (grant both to
`admin_finance`) and is exactly what produced the current bug: two
namespaces drifting independently across nav/route-guard/action-menu/
backend checkpoints with no single source of truth. A future addition of
a new Security Deposit surface would have no way to know which namespace
to check. One canonical namespace, with the alias's constants frozen
(deprecated, not deleted) and pinned by an automated guard, is the only
approach that actually closes the drift risk permanently.

## Migration strategy

1. **Backend**: block the 4 `package_commerce` endpoints with `410`
   (matching the FINAL-L5-05H `engine_deduct_wallet` precedent — real
   transactional-integrity defect + zero real caller = block, don't leave
   reachable). Migrate `platform_commerce.admin_adjust_deposit` from
   `require_super_admin` to `require_permission(P.FINANCE_DEPOSITS_UPDATE)`.
   Remove the two now-fully-orphaned `tenant_engine.admin_service` methods
   (`get_security_deposit`/`mark_deposit_paid` — their routes were already
   removed in an earlier "Phase 4 finance certification" sprint, per a
   comment already in the codebase; the service methods survived as dead
   code until now).
2. **Role bundles**: `admin_finance` keeps only the 4 canonical
   `FINANCE_DEPOSITS_*` keys (the 8 deprecated ones removed — they
   authorized nothing regardless). `admin_readonly` migrated from the dead
   `FINANCE_SECURITY_DEPOSITS_READ` to canonical `FINANCE_DEPOSITS_READ`
   (a real fix — Read Only's existing read-only intent now actually
   works). `admin_operations`/`admin_security` confirmed to hold zero
   deposit permissions (unchanged).
3. **Frontend**: nav item, `RequirePermission` page guard, and permission
   catalog all migrated to `finance:deposits:read`. Two previously-ungated
   controls fixed: the deposits list page's Export button (now gated on
   `finance:hub:export`) and the Tenant Detail page's "Adjust Security
   Deposit" menu item (now gated on `finance:deposits:update` — it
   previously rendered for every role that could reach the page,
   regardless of Security Deposit permission, relying solely on the
   backend's coarse `require_super_admin` to deny the actual mutation).
   Dead client methods (`adminTenantApi.getSecurityDeposit`/
   `markDepositPaid`, targeting the now-blocked routes) removed.
4. **Cross-tenant fix**: `CommerceService` gained `actor_tenant_id`
   tracking and an `_assert_owns_tenant_deposit()` check (mirroring
   `ServiceabilityService._assert_owns_tenant()`'s established pattern
   exactly), applied to the 3 read/initiate deposit methods, scoped to
   `actor_role == "tenant_owner"` only — admin/super_admin callers are
   unaffected and continue to read across tenants as intended.

## Compatibility period

None. Verified before blocking: zero real frontend caller anywhere in the
codebase depended on any of the 4 `package_commerce` security-deposit
routes (`git grep` confirms `adminTenantApi.getSecurityDeposit`/
`markDepositPaid` — the only client methods that ever targeted them —
were themselves already dead code with zero callers). A time-bounded
compatibility adapter would add pure overhead with no protective value
per mission rule 19 ("compatibility adapters must be explicit and
temporary" implies protecting a real caller; none existed here) — same
reasoning already applied in FINAL-L5-05T for the Service Area shadow
routes.

## Role impact

- `admin_finance`: no functional change (already held both namespaces via
  05O's bounded fix; now holds only the canonical one, which was always
  the one that actually worked).
- `admin_readonly`: **functional fix** — can now actually read the live
  Security Deposits console end-to-end (previously held a permission that
  authorized nothing).
- `admin_operations`, `admin_security`: no change (correctly zero deposit
  permissions, confirmed unchanged).
- `super_admin`: no change (wildcard `P.ALL` unaffected).
- `tenant_owner`: no permission change, but a real cross-tenant read
  vulnerability closed — self-service deposit access is now correctly
  scoped to the caller's own tenant.

## Rollback plan

`FINANCE_SECURITY_DEPOSITS_*` constants remain defined and could be
re-wired to role bundles in a single revert if ever needed, though doing
so would reintroduce the exact namespace-drift bug this sprint closed —
not recommended. The 4 blocked `package_commerce` routes retain their
full original request/response contract in git history (this commit and
all prior) if the transactional-integrity defect were ever independently
fixed and the routes deliberately un-blocked; recommended path instead is
building any missing capability directly into the canonical
`finance_hub`/`FinanceHubService` implementation, which already has the
richer feature set.
