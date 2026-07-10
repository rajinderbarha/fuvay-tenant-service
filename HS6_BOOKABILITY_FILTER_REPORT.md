# HS6 — Bookability Filter Report

## Confirmed real, pre-existing
`_passes_full_eligibility_gate()` checks
`provider_visibility_statuses.is_bookable` first — any tenant without a
`true` value is excluded from the candidate pool before any other check
runs. This is real, unchanged, confirmed via source read this sprint.

## Real data-source inconsistency found (not fixed)
The rest of `_passes_full_eligibility_gate()` re-derives bookability-
adjacent signals from a **different set of tables** than
`_evaluate_provider_bookability()` (fixed in HS4B):

| Signal | HS4B's `_evaluate_provider_bookability` | This eligibility gate |
|---|---|---|
| Usage credits | `tenant_billing.credit_balance` | `tenant_wallets.credit_balance` |
| Security deposit | `tenant_billing.security_deposit_paid` | `security_deposits.status` |
| Package/plan | (not checked directly) | `tenant_package_assignments.status` |

If `tenant_wallets`/`security_deposits`/`tenant_package_assignments` are
stale, unpopulated, or diverge from `tenant_billing` for any tenant, the
`is_bookable` flag from `provider_visibility_statuses` (which the gate
DOES check first) could say "bookable" while these secondary checks
still reject the candidate — or vice versa in a differently-configured
tenant. Not verified whether these tables are kept in sync with
`tenant_billing` anywhere in the codebase. This is a real, confirmed
architectural risk, not fixed this sprint (unifying two independent
bookability computation paths is a larger, riskier change than this
sprint's remaining time budget allows safely).

## Verdict
Bookability filtering: **real and functioning** (uses the HS4B-fixed
`is_bookable` flag as a hard gate), but layered on top of a **second,
independent set of checks using different tables** — a real
inconsistency risk, documented for a future unification sprint rather
than fixed here.
