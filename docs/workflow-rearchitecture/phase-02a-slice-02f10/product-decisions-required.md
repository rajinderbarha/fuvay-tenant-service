# Product Decisions Required — Slice 2F-10

1. **Should `add_customer_message` also block on `resolved`/`settled`?**
   Same open question as Slice 2F-9A's provider-side item 1 — not
   decided, not changed, applies symmetrically here since both methods
   use the identical `FINAL_STATUSES` pattern.

2. **[RESOLVED IN SLICE 2F-10A — not actually a product decision.]** Was:
   "Should `check_eligible`'s additional policy be wired into
   `create_complaint`?" Slice 2F-10A found real evidence
   (`ELIGIBLE_STATUSES`' documented bug-fix history, the `ComplaintPolicy`
   model's production-grade design, and pre-existing but unused error
   constants) that `check_eligible` is CANONICAL_CREATION_POLICY, not
   advisory — so this was a security gap, not a product question. Fixed.

3. **[RESOLVED IN SLICE 2F-10A — investigated, not a defect.]** Was:
   "Should `create_refund_request_from_complaint`'s silent no-op instead
   raise?" Slice 2F-10A found direct, existing test evidence
   (`test_refund_events_log_the_status_actually_applied`'s own docstring)
   that this is deliberate, load-bearing behavior across the whole
   refund lifecycle. No change made.

4. **[RESOLVED IN SLICE 2F-10A — answered by existing code, not a
   product decision.]** Was: "Duplicate open complaints remain allowed
   at creation time." Slice 2F-10A found the duplicate-open-complaint
   guard is now enforced at creation (via the `check_eligible` fix
   above); its scope to `OPEN_STATUSES` (allowing a new complaint once a
   prior one of the same type is resolved/closed/cancelled/rejected) is
   existing, deliberate policy — see
   `phase-02a-slice-02f10a/duplicate-complaint-behavior.md`.

5. **`complaints.admin_router`'s own boundary** was re-confirmed
   (`require_super_admin`-gated throughout) but not independently
   re-audited end-to-end this slice — out of scope per the mission's
   explicit instruction.
