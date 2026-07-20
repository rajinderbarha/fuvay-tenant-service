# Product Decisions Required — Workstream 9 (not resolved this slice)

These are decisions for a future product/policy slice. Per the explicit
out-of-scope instructions ("do not grant FINANCE_PAYOUTS_* permissions",
"do not grant FINANCE_CLAIMS_* permissions", "do not add new finance
permissions"), **none of these were resolved or acted on this slice.**

## 1. Should `admin_finance` be granted payout actions?
`FINANCE_PAYOUTS_APPROVE/REJECT/PROCESS/COMPLETE` are currently reachable
only via `super_admin`. If the product intent is for a dedicated finance
admin to run day-to-day payout operations without needing super_admin,
this permission set is the natural candidate to grant. Counter-
consideration: payout completion moves real money externally and is
irreversible — the interim policy explicitly names payout
approval/completion as an example of an action that should stay
super-admin-only "unless already explicitly granted."

## 2. Should `admin_finance` be granted warranty-claim actions?
`FINANCE_CLAIMS_ASSIGN/APPROVE/REJECT/SETTLE` are currently super_admin-
only. Claim settlement draws from a security deposit and creates a real
payment/credit — same irreversibility concern as payouts. Assignment and
document-request are lower-risk (metadata-only, reversible) and could
plausibly be split out from approve/reject/settle in a future slice.

## 3. Should assign/request-documents be split from approve/reject/settle?
If a future slice wants finer granularity, `FINANCE_CLAIMS_ASSIGN` could
be decoupled from `FINANCE_CLAIMS_APPROVE`/`REJECT`/`SETTLE` so a finance
admin can triage/route claims without being able to approve payouts of
money — not evaluated further here, as it requires defining a new
permission (out of scope this slice).

## 4. Maker-checker / dual control
The interim policy explicitly defers this: "A future maker-checker or
dual-control design is a separate product phase and must not be invented
here." Not designed, not stubbed, not implemented this slice.

## 5. `approve_payout`'s unbounded client-supplied `approved_amount`
Flagged in `amount-currency-integrity.md` as a potential (not
conclusively proven) integrity gap — whether an explicit upper-bound
check against the originally requested amount is intended product
behavior is a decision for the team that owns the payout model, not
inferable from source alone.

## Recommendation (non-binding)
If the product team wants to reduce super_admin's operational load,
granting `FINANCE_CLAIMS_ASSIGN`/`FINANCE_CLAIMS_REJECT` (both reversible,
non-money-moving) to `admin_finance` first — before touching
`APPROVE`/`SETTLE`/any `FINANCE_PAYOUTS_*` — would be the lowest-risk
next step. This is a suggestion for future scoping, not a decision made
or acted on in this slice.
