# Known Limitations — Slice 2F-5B

1. **`package_commerce`/`platform_commerce` delegation not traced.**
   `adjust_deposit`, `approve_claim`, and `reject_claim` all delegate into
   `self._commerce` (a `CommerceService` instance living outside
   `finance_hub`). Their internal amount/state validation was not read or
   tested this slice — `package_commerce.admin_router` was explicitly out
   of scope for modification and deep audit.

2. **UI-level role-based button gating not independently verified.**
   Backend 403 enforcement was fully verified for all 17 mutations across
   all 12 personas. Whether the super-admin Next.js app additionally
   hides (vs. merely disables-on-403) mutation buttons per role was not
   traced component-by-component — a UI redesign was explicitly out of
   scope, and the backend gate is the authoritative enforcement point.

3. **No independent concurrency/locking test.** The absence of row-level
   locking in the mutation methods was confirmed by source inspection,
   not exercised under real concurrent load. This is a platform-wide,
   pre-existing pattern, not unique to finance_hub.

4. **`approve_payout`'s `approved_amount` upper bound.** No explicit cap
   against the originally requested amount was found when the caller
   supplies `approved_amount` explicitly (only the default falls back to
   the requested amount). Not conclusively provable as a defect within
   this slice's evidence; logged for future review, not remediated.

5. **Frontend caller attribution not independently re-verified
   per-individual-endpoint beyond path-string matching.** Confirmed all
   17 API client functions call the correct path; did not trace every
   calling component's own auth-context checks.

6. **Product-policy questions left open by design**, per the interim
   least-privilege policy: whether `admin_finance` should ever be granted
   `FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` remains unresolved (see
   `product-decisions-required.md`) — this is a deliberate, policy-driven
   non-closure, not an oversight.
