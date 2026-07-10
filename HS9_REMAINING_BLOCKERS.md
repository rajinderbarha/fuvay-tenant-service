# HS9 — Remaining Blockers

1. **No dedicated `test_hs9_*.py` test file was written.** Live/manual
   verification was thorough (see the live verification report), but no
   automated regression coverage exists yet for the deduction resolver,
   idempotency, or the `service_started`-transition fix specifically.
2. **No tenant/admin finance UI.** Both new read endpoints
   (`/usage-credits/balance`, `/usage-credits/ledger`, plus the admin
   equivalent) are real and live-verified, but nothing renders them.
3. **No customer rating/review flow** for Home Services bookings —
   not attempted this pass.
4. **Low/insufficient-credit policy is implemented but not enforced
   anywhere else.** The recommended policy ("never block completion over
   low credits, just record it") is followed — completion always
   succeeds and the balance can go negative — but there is no
   "restrict future matching for low/negative-credit tenants" logic
   anywhere in HS6/HS6B's matching engine. This is the ticket's own
   stated policy's second half, left unimplemented and explicitly
   flagged here rather than silently dropped.
5. **`amount_difference_reason`/`approved_extra_charges`/`discount_reason`**
   (collected-amount-vs-selected-price reconciliation) — not
   implemented, inherited from HS8B's own documented gap.
6. **No admin cross-tenant deduction list or job-audit-plus-ledger join.**
7. **`created_by` on `usage_credit_ledger` is never populated** — the
   column exists but `deduct_for_completed_job()` doesn't pass an actor
   ID (deduction is system-triggered, not a specific user's action, so
   this may be correct-as-is, but it's worth flagging since the ticket
   listed it as a required field).
8. **`zone_id` on the ledger is schema-only** — no zone/tier concept
   exists in the pricing-rule resolution yet, consistent with pricing
   engines elsewhere in this codebase not having zone-based rules
   populated for this dev tenant.

## What is solid and fixed this pass
- **Completed Job Deduction resolves correctly with real specificity
  enforcement** — live-verified against the ticket's own named failure
  mode ("Window AC LG deduction must not be used for Split AC LG") using
  two distinct real pricing rules with different specificity levels.
- **A real bug found and fixed**: `service_started` was declared
  completable by HS8B but its transition graph didn't actually allow
  reaching `completed` from there — a job could get stuck unable to
  complete from a state HS8B itself said was valid.
- **Deduction is atomic with completion** — a job can never be marked
  completed without an immediate, same-transaction deduction attempt.
- **Idempotency enforced at two independent layers** (job-status
  terminality + a real database unique index on the ledger).
- **Ledger arithmetic verified correct**: `balance_after ==
  balance_before + credit_delta` held exactly in the live test
  (`4000 - 21 = 3979`).
- **Reused the pre-existing, real `tenant_billing.credit_balance`**
  field rather than introducing a second, competing balance — avoiding
  the parallel-data-model bug pattern found repeatedly in earlier HS
  sprints this session.
- Zero regressions; 295/295 passing.
