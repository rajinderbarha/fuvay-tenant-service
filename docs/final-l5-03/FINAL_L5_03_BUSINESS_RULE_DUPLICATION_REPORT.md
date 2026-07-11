# FINAL-L5-03 — Business Rule Duplication Scan

Real grep scan this sprint for fee/deduction/health/pricing arithmetic patterns across `frontend/*/app` and `frontend/*/components`, each match individually inspected (not classified by keyword alone).

## Findings

| Location | Pattern | Classification |
|---|---|---|
| `admin/pricing/bargain-rules/page.tsx:390` | `Number(form.customer_min_price) * (1 + Number(form.platform_fee_percent) / 100)` | **DISPLAY_ONLY / SAFE_CLIENT_VALIDATION** — an instant "what would this look like" hint shown while the admin types into a rule-configuration form, immediately followed by a real "Evaluate Offer" action (`perm.has("pricing.bargain_rules.evaluate_preview")`) that calls the actual backend preview endpoint (`previewResult.platform_fee_amount`, a *different* variable, backend-sourced) before the rule can be saved. Not authoritative — the real fee calculation used at save-time is backend-side. |
| `admin/home-services/price-experience/page.tsx` | `platform_fee_percent`/`platform_fee_on_min`/`platform_fee_on_max` fields | **DISPLAY_ONLY** — `result.platform_fee_on_min`/`result.platform_fee_on_max` are read from an API response object (`result`), not computed client-side; this page displays backend-computed values, doesn't recompute them |
| `admin/home-services/pricing-rules/page.tsx:100` | `const fee = Number(f.platform_fee_percent), deduction = Number(f.completed_job_deduction_credits)` | **SAFE_CLIENT_VALIDATION** — reads form input values into local variables for client-side form-completeness validation (e.g. "is this field filled in") before submission, not used to calculate an actual charge/deduction applied to any account |
| `admin/operations/[jobId]/page.tsx:165,175` | `j.minutes_in_status > j.sla_minutes * 0.75` | **SAFE_CLIENT_VALIDATION / DISPLAY_ONLY** — a UI color-coding threshold (amber warning past 75% of SLA time), not a business rule that affects any persisted state or charge |
| `admin/tenants/[id]/page.tsx:1369` | `(billing.data.commission_rate * 100).toFixed(1)` | **DISPLAY_ONLY** — formats an already-backend-computed rate as a percentage string for display, doesn't compute the rate itself |
| Various `pricing-tiers`/`pricing/bargain-rules` pages | `platform_fee_percent`, `commission_rate` as **form input fields** | **DISPLAY_ONLY / SAFE_CLIENT_VALIDATION** — these are admin-editable *configuration inputs* (the admin is setting the rule's fee percentage), not calculations of an actual transaction's fee |

## Domains explicitly checked, none found duplicated client-side as authoritative
- Platform fee: form inputs + preview reads only (see above) — no client-side authoritative fee computation applied to a real transaction found.
- Low/Mid/High price generation: not found duplicated in frontend (confirmed the `price-experience` page reads `result.*` from an API response).
- Provider price floor/range: read-only display in every page checked.
- Matching eligibility: not found in frontend — all matching logic is backend (`match-and-price` endpoint, confirmed in FINAL-L5-02B).
- Usage credit deduction: `usage_credit_balance`/`completed_job_deduction` are always read from API responses (`usageCreditsApi.getBalance()`, ledger entries), never recomputed client-side — confirmed directly in this sprint's own `TenantLayout` fix (the fix specifically avoided introducing any client-side balance math).
- Tenant readiness/health score/badge qualification/availability eligibility/cancellation policy: not found computed client-side in this sprint's scan; all read from `providerStatusApi`/`tenantApi.getHealth()`-style backend responses.

## Result
No `DUPLICATED_AUTHORITATIVE_RULE` found. All fee/rate/deduction-adjacent frontend code is either a backend-response display, a non-authoritative live-preview hint (immediately followed by a real backend evaluation step before anything is saved), or a pure UI threshold with no business consequence.
