# Phase 4 — Finance Backend Report (Packages, Usage Credits, Security Deposit)

## Architecture note (read first)

This is **not greenfield**. Before writing any code, a full research pass
confirmed Packages, Usage Credits (as tenant credit wallets), and Security
Deposits are already built end-to-end (DB → engine → admin API → frontend)
under the `package_commerce` + `platform_commerce` engines — just with
different field/route names than this ticket's prompt assumed (e.g.
`included_credit_amount` not `included_usage_credits`, `slug` not
`package_code`, `/credit-wallet` not `/finance/usage-credits`). This report
documents the real, working system, the bugs found and fixed in it, and the
honest mapping between the ticket's assumed names and the real ones.

## Module 1 — Package / Plan Management

**Real route**: `/admin/packages` (frontend), `/v1/admin/packages*` (backend) — matches.

**Endpoints** (all real, all live-verified after fixes):
`GET/POST /v1/admin/packages`, `GET/PUT/DELETE /v1/admin/packages/{id}`,
`POST .../activate`, `.../deactivate`, `.../clone`,
`GET/POST/PUT/DELETE .../features[/{id}]`, `GET/POST/PUT/DELETE .../limits[/{id}]`,
`GET /v1/admin/packages/summary`, `GET /v1/admin/packages/audit-logs` (**new this sprint**),
`GET /v1/admin/packages/{id}/audit` (**new this sprint**),
`GET /v1/admin/packages/purchases` (**new this sprint** — was missing, frontend called a 404/500),
`GET /v1/admin/tenants/{tenant_id}/packages/purchases` (**fixed this sprint** — was 500).

**Baseline package** — confirmed live:
```
name: "Starter Home Services", slug: "starter_home_services"
package_type: "subscription", vertical_type: "home_services"
included_credit_amount: 1000.0, security_deposit_amount: 5000.0
is_active: true
```
This maps to the ticket's `included_usage_credits=1000`,
`security_deposit_required=true` (real schema stores an *amount*, not a
boolean — `amount > 0` is the "required" signal), `package_code` (real: `slug`).
Only 1 row exists — no duplicates.

**Package Limits** (Module 2) — the ticket's `staff_limit`/`service_area_limit`
map to generic `PackageLimit` rows (`limit_key`/`limit_value`), not dedicated
columns. **Gap found and fixed this sprint**: neither limit existed on the
baseline package. Created both via the real, audited API:
`staff_limit = 5`, `service_area_limit = 5` — confirmed live afterward.

## Module 3 — Package Activation Rules (config only, per ticket's explicit scope)

Real mechanism: `TenantPackageAssignment.status` lifecycle
(`selected → pending_review → pending_payment → paid_pending_approval →
active → expired/cancelled/refunded/rejected`), with an explicit model
docstring: *"starts_at and expires_at MUST remain NULL until admin approval.
Credits are added to wallet only on activation (admin approval)."* This is
the real implementation of `starts_after_admin_approval` /
`included_credits_added_after_approval` — as lifecycle-state logic, not
boolean config columns. Confirmed live: Demo AC Services' assignment has
`status: "pending_approval"`, `starts_at: null`, `activated_at: null`,
`included_spendable_credits: 0` — exactly matching the ticket's expected
"package selected but not active" baseline. **Actual activation is
correctly out of this phase's scope** (Phase 5, per the ticket itself).

## Module 4/5/6 — Usage Credit Balance / Ledger / Top-up / Adjustment

Real routes: `GET/POST /v1/admin/tenants/{tenant_id}/credit-wallet`,
`GET .../credit-ledger`, `POST .../credit-wallet/top-up`, `POST .../credit-wallet/adjust`.

Baseline confirmed live: Demo AC Services has **no wallet row** before
approval → `GET .../credit-wallet` returns `404 CREDIT_WALLET_NOT_FOUND`
(lazy-created on first credit, per the ticket's own acceptance: "balance
exists or is created lazily"). Ledger returns `{"items": [], "total": 0}`.

**Full top-up/adjust/revert cycle live-tested**:
1. `POST .../top-up` `{"amount":100,"reason":"Phase 4 certification test top-up"}` → wallet created, `balance: 100.0`.
2. Ledger shows 1 `credit` entry, `balance_before:0, balance_after:100`.
3. `POST .../adjust` `{"entry_type":"debit","amount":100,"reason":"...revert"}` → `balance: 0.0`.
4. `POST .../adjust` `{"entry_type":"debit","amount":50,...}` (would go negative) → **correctly rejected**, `402 COMMISSION_WALLET_EMPTY`, `request_id` present (see bug fix below — this used to 500).
5. Real audit log entries confirmed for both top-up and adjust, each carrying the mutation's own `request_id`.

## Module 7 — Completed Job Deduction Rule (read-only linkage)

No dedicated `/finance/completed-job-deduction-rules` endpoint exists (and
none was built this sprint — the ticket scopes this module to *reading*
existing configuration, and the data already lives on, and is already
API-exposed by, the Phase 3-certified `pricing-rules` endpoints). Confirmed
live: `GET /v1/admin/pricing-rules?master_service_id=<AC Repair>` →
`completed_job_deduction_credits: 21`; `job_credit_deduction_trigger =
"job_completed"` confirmed via `GET /v1/admin/settings`. No new endpoint was
fabricated to "look complete" — the real data is genuinely there and
genuinely reachable, just via the Phase 3 pricing-rules surface rather than
a new Phase-4-specific one.

## Module 8/9/10 — Security Deposit Config / Records / Hold-Release-Adjust

Real routes: `GET /v1/admin/tenants/{tenant_id}/security-deposit`,
`POST .../mark-paid`, `.../refund`, `.../forfeit`.

Baseline confirmed live: Demo AC Services deposit — `required_amount: 5000.0,
status: "unpaid", total_paid: 0.0` — separate record from the wallet (see
Module 4), never merged into the credit balance.

**Critical bug found and fixed** (route collision): `tenant_engine/admin_router.py`
defined `GET /{tenant_id}/security-deposit` and `POST .../security-deposit/mark-paid`
at the *exact same paths* as `package_commerce`'s versions, registered
*earlier* in `main.py`, silently shadowing the real, permission-gated,
audited, envelope-wrapped implementation. The shadowed duplicate returned a
bare dict with no `request_id`/`success` envelope at all. Removed the 2
duplicate routes from `tenant_engine`; confirmed live afterward that the
canonical `package_commerce` endpoint now responds with the full envelope
and a real `request_id`.

**Second bug found and fixed** (copy-paste audit labels): `admin_refund_deposit`
and `admin_forfeit_deposit` both logged `action="security_deposit_paid"`
instead of their own distinct action names — fixed to
`"security_deposit_refunded"`/`"security_deposit_forfeited"`.

## Permissions (new this sprint)

Added `PACKAGES_READ/CREATE/UPDATE/ARCHIVE/ACTIVATE/DEACTIVATE/CLONE/AUDIT_READ`
and `FINANCE_USAGE_CREDITS_READ/TOP_UP/ADJUST/LEDGER_READ`,
`FINANCE_COMPLETED_JOB_DEDUCTION_RULES_READ`,
`FINANCE_SECURITY_DEPOSITS_READ/CONFIG_UPDATE/CREATE/MARK_RECEIVED/HOLD/RELEASE/ADJUST/AUDIT_READ`,
`FINANCE_SETTINGS_READ/UPDATE` to `app/core/permissions.py`, and wired every
package/wallet/deposit endpoint in `package_commerce/admin_router.py` from
bare `require_super_admin`/`get_current_user` to `require_permission(P.*)`.
Commission/storage-quota endpoints (job/finance *runtime*, explicitly out of
Phase 4 scope) were left untouched.

## Result: **Backend certified**, 6 real bugs found and fixed (detailed in `PHASE_4_FINANCE_BUG_FIX_REPORT.md`).
