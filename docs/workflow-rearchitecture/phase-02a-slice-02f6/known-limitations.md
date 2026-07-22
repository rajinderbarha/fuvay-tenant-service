# Known Limitations — Slice 2F-6

1. **Frontend "Issue" button not hidden from non-owner accounts.**
   The backend now correctly rejects a staff user's issue attempt (403),
   but the tenant-portal UI does not hide the button for that role. Not
   fixed — frontend redesign out of scope; backend is authoritative.

2. **No positive-amount validation on payment/invoice-item amounts.**
   `collected_amount`, `unit_price`, `quantity` are trusted, unvalidated
   client input. Pre-existing, not introduced this slice; no existing
   in-file precedent to safely mirror a fix from.

3. **No per-job-assignment restriction for staff/technician actions.**
   Any staff/technician in the correct tenant can act on any invoice in
   that tenant, not just jobs they are personally assigned to. Consistent
   with the existing `FIELD_OPS_JOBS_CLOSE` permission's own scope (which
   also has no per-assignment restriction) — not a new gap, not fixed.

4. **18 other tenant-facing modules remain unprotected or partially
   protected**, ranked in `remaining-module-priority-matrix.csv`. Only
   `invoice_payment.provider_router` was investigated and fixed this
   slice, per the mission's "select exactly one module" instruction.
   Several "unknown" cells in that ranking reflect a deliberately shallow
   pass on modules not selected — future slices should re-verify before
   acting on those rankings.

5. **Platform-wide 261 `UNVERIFIED` mutation routes remain** (per the
   tool's own auto-classification), spanning modules well beyond this
   slice's scope — not claimed as addressed.

6. **Product-policy question left open by design**: whether `staff`
   should ever be granted `FIELD_OPS_INVOICE_GEN` remains unresolved
   (see `product-decisions-required.md`) — a deliberate, policy-driven
   non-closure, not an oversight.
