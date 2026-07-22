# Known Limitations — Slice 2F-10A

1. **Duplicate-open-complaint check has a concurrency race** (no
   row/advisory locking) — documented, not fixed (no migration/constraint
   permitted this slice). See `duplicate-complaint-behavior.md`.
2. **`add_customer_message`'s resolved/settled question remains
   genuinely open** — not decided, not changed.
3. **`ComplaintPolicy.get_complaint_policy`'s `tenant_id` parameter is
   accepted but never used in its actual query** — a pre-existing, dead
   parameter noticed during this slice's investigation but out of scope
   to fix (not part of the eligibility bypass this slice targets, and
   fixing it could change which policy row resolves for existing
   tenants — a product-policy-adjacent change, not a security defect).
4. **Frontend refund-UI's "no amount/approval control" claim was not
   exhaustively line-reviewed** — based on the API client's exports
   only, not a full component read.
5. **10 live-database-only test files remain unexecutable in this
   environment** — reviewed and confirmed irrelevant to this slice's own
   gates (see `live-database-test-limitations.md`), not fixed or worked
   around.
