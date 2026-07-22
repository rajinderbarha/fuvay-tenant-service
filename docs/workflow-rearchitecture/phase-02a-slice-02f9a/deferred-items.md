# Deferred Items — Slice 2F-9A

Explicitly deferred, per the out-of-scope list and this slice's own
findings — none of these were investigated, designed, or acted on:

1. `complaints.customer_router` — not begun or modified (confirmed as
   the recommended next slice, again).
2. `complaints.admin_router` — not modified (confirmed
   `require_super_admin`-gated throughout, stronger boundary).
3. `execution.real_estate_router` — not begun.
4. No new complaint permission was created; no capability was granted to
   staff or technicians; no new role was introduced.
5. No internal-note system or new dispute interface was built.
6. No refund or cash-payment behavior was created; the internal-credit
   settlement model was not changed.
7. Complaint, warranty, and rework models were not merged;
   Booking/Job/ServiceBooking/ServiceJob were not merged.
8. Booking Exception Resolution, Admin/Tenant My Work, and Next-Action
   aggregation were not implemented.
9. `readonly@demo-ac-services.local` was not remediated; migration 144
   was not applied.
10. No visual redesign occurred.
11. `create_settlement_proposal`/`respond_to_settlement`'s own
    state-machine completeness was not independently re-audited (only
    confirmed unreachable from the 2 target methods).
12. Full-fidelity frontend state-awareness for `offer_resolution`
    (2-state legal-source gating instead of the coarser 3-state final
    check) — flagged as a product decision, not built.

## Documentation Corrections applied to Slice 2F-9 (not deferred — done)
- `phase-02a-slice-02f9/known-limitations.md` items 1 and 4 corrected.
- `phase-02a-slice-02f9/complaint-state-machine.md`'s Conclusion
  corrected.
- `phase-02a-slice-02f9/approval-gate.md`'s status header and
  `DOMAIN_INTEGRITY_CLOSED` reasoning corrected/annotated.
- `phase-02a-slice-02f9/deferred-items.md` items 11 and 12 marked
  resolved.
