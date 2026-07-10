# HS9B — Remaining Blockers

## Closed this pass (all 5 of HS9's original blockers)
1. ~~No tenant finance UI~~ — **FIXED.** Real bug found (page called a
   disconnected legacy "wallet" endpoint) and fixed; page now shows real
   balance + ledger.
2. ~~No admin finance UI~~ — **FIXED.** New `/admin/finance/usage-credits`
   page, real ledger + add-credits action.
3. ~~No customer rating/review flow~~ — **FIXED.** Real endpoints
   wrapping the existing certified Review Engine, all 3 required
   scenarios (submit/duplicate/incomplete-booking) live-verified.
4. ~~No automated test_hs9_*.py file~~ — **FIXED.** 15 new tests, all passing.
5. ~~Low-credit policy does not restrict future matching~~ — **Found
   already implemented from HS4B** (not previously recognized as such
   in HS9's own report) and **live-verified end-to-end this pass**: a
   zero-credit tenant is genuinely excluded from matching, and becomes
   matchable again once credits are restored. Enhanced with a specific
   `INSUFFICIENT_USAGE_CREDITS` reason code for diagnosability.

## Still open (documented, not fabricated)
1. **Job-detail-level finance integration** — HS8B's job detail page
   shows Completion Proof (work summary, collected amount) but not the
   Completed Job Deduction credits or a link to that job's specific
   ledger entry.
2. **No cross-tenant admin finance aggregate views** — "Total Usage
   Credits Deducted platform-wide," "Tenants With Low Credits," and
   "Failed Deduction Events" summaries don't exist; no backend endpoint
   powers them. Only a per-tenant search view exists.
3. **No multi-tier credit-status classification**
   (`HEALTHY`/`LOW_CREDIT`/`INSUFFICIENT_CREDITS`/`SUSPENDED_FOR_CREDITS`)
   or configurable thresholds — the real, working policy today is a
   simpler binary `credit_balance > 0` gate (from HS4B). The ticket's
   richer model is not implemented.
4. **No customer-facing UI** for the review flow — same established gap
   from every HS sprint touching the customer surface this session; the
   API is real and live-verified, nothing renders it.
5. **Permission-aware UI/RBAC not investigated** — unchanged from every
   prior HS8/HS9 report.
6. **No frontend test spec files** (`*.spec.ts`) — TypeScript compile
   used as the correctness signal instead, consistent with this
   session's established pattern (no evidence any HS sprint this
   session successfully ran `npm test`).
7. **Ledger table columns missing human-readable service/type/brand
   names** — only raw UUIDs are shown (`service_id`, `service_type_id`,
   `brand_id` truncated to 8 chars) in both the tenant and admin ledger
   tables, since the backend ledger entries don't carry joined names.

## What is solid and fixed this pass
- Real bug found and fixed: tenant finance UI was wired to a
  disconnected legacy endpoint.
- Real, new admin finance UI with a working add-credits action against
  a pre-existing, real backend endpoint.
- Real, live-verified, three-scenario customer review flow.
- Real, live-verified, full round-trip low-credit matching restriction
  (exclude → restore → matchable again) — the ticket's single hardest
  gate ("must not keep receiving future matched jobs") is genuinely
  satisfied, discovered to already exist from HS4B and confirmed working
  end-to-end for the first time in this session.
- 15 new passing tests; 0 TypeScript errors in both frontends touched.
