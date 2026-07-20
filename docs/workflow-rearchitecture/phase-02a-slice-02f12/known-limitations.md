# Known Limitations — Slice 2F-12

1. **`cancel_appointment` is not assignment-limited** (any tenant_owner/
   staff, not just the assigned one, may cancel) — documented, not
   fixed, since it's plausibly intentional business design and the
   persona-layer fix already closes the security-relevant gap. See
   `product-decisions-required.md` item 1.
2. **`app.engines.coaching_appointment`'s own authorization pattern was
   documented, not evaluated or hardened** — out of scope (no capability
   overlap exists to require it).
3. **No frontend surface exists for any route in this module** — reads
   and mutations alike remain backend-only in terms of active UI
   callers.
4. **Business-wide staff/owner read access is not assignment-limited**
   (any tenant_owner/staff can read any appointment's timeline within
   their own tenant, not just their own assigned ones) — a deliberate,
   evidence-supported design choice (back-office visibility), matching
   the identical real-estate precedent, not a defect.
