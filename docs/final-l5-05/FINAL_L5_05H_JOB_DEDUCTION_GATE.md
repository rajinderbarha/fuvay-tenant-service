# FINAL-L5-05H — Part 7 P0 Gate: Job-Deduction Architecture Comparison

## Verdict: DEPRECATE_AND_BLOCK — implemented

## The two paths, compared with real evidence

| | Canonical: Completed Job Deduction | Non-canonical: `engine_deduct_wallet` |
|---|---|---|
| File | `app/engines/execution/usage_credit_deduction.py:67` | `app/engines/platform_commerce/service.py:372` |
| Entry point | Called in-process from `home_service_service.py:608`, inside the real job-completion flow | `POST /v1/commerce/tenants/{tenant_id}/wallet/deduct`, `require_super_admin` only |
| Writes to | `tenant_billing.credit_balance` + `usage_credit_ledger` | `TenantWallet.credit_balance` + `wallet_transactions` (via `ledger.debit_wallet`) |
| Idempotency | Checks for existing `UsageCreditLedger` row with `event_type="completed_job_deduction"` for the job before writing | Unique `idempotency_key = f"engine_deduct:{job_id}"` on `wallet_transactions` |
| Amount source | Resolved from `ServicePricingRule` via specificity hierarchy (service+type+brand > service+type > service) | Caller-supplied `amount` in the request body — no independent pricing resolution |
| Internal callers (grep, whole repo) | 1 (`home_service_service.py`) | **0** — only the function definition and its own route registration match `engine_deduct_wallet`/`wallet/deduct` anywhere in `app/` |
| Test coverage (grep `tests/`) | Covered by execution/deduction test suites | **0 matches** for `wallet/deduct` or `engine_deduct` anywhere in `tests/` |

## Finding

`engine_deduct_wallet` is not wired into job completion, force-close, or void anywhere in the
codebase. It is a live, callable, super-admin-gated HTTP endpoint with zero automatic trigger and
zero test coverage. Because it posts to a different ledger (`wallet_transactions`) than the
canonical Completed Job Deduction (`usage_credit_ledger`), if it were ever accidentally wired into
the job-completion path in a future change, a single job could receive two independent,
non-cross-checked deductions — violating the mission's required invariant ("one service job may
create at most one valid Completed Job Deduction").

No duplicate-charge bug exists in production today (zero automatic callers = zero real risk right
now), but the endpoint's `[Internal engine use]` naming actively invites a future engineer to wire
it up incorrectly.

## Action taken

`POST /v1/commerce/tenants/{tenant_id}/wallet/deduct` now returns `410 Gone` unconditionally,
with a message pointing callers at the canonical
`app.engines.execution.usage_credit_deduction.deduct_for_completed_job`. The underlying
`CommerceService.engine_deduct_wallet` method and `ledger.debit_wallet` primitive were left
untouched (not deleted) — `debit_wallet` is shared with commission processing and other consumers
(see FINAL_L5_05G_WALLET_ARCHITECTURE_INVESTIGATION.md) and removing it is out of scope for this
gate. Only the specific job-linked-deduction entry point was blocked.

Verified via:
- `python -c "import app.engines.platform_commerce.router"` — imports cleanly.
- `pytest tests/test_final_l5_05b_jobs_ia_guard.py` — 10/10 passed (Jobs domain regression unaffected).
- `pytest tests/ -k "commerce or wallet or usage_credit or deduction"` — 130/130 passed.
- Full suite rerun: **9005 passed, 1 skipped, 0 failed** in 583.24s — exact match to the FINAL-L5-05E/F/G baseline, confirming zero regressions from this change.

## Scope note

This gate is Part 7 of a 37-part mission. The remaining parts (full consumer classification with
formal per-consumer disposition, endpoint/data-model/mutation-graph inventories, package/commission/
Security Deposit/health-signal domain-boundary decisions, domain-service extraction, generic wallet
API deprecation beyond this one endpoint, DB-level enforcement, RBAC/audit hardening, and 4-role
Chromium E2E) were not attempted this session. See `FINAL_L5_05_REMAINING_BLOCKERS.md` Blocker 9
for the carried-forward scope.
