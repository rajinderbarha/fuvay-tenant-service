# Product Decisions Required — Slice 2F-10A

1. **`add_customer_message`'s resolved/settled behavior** — remains
   undecided; no new evidence found this slice. Carried over from Slice
   2F-9A/2F-10.
2. **Whether a resolved complaint should permit a new complaint of the
   same type** — this slice found the *existing* answer is yes (the
   duplicate-open-complaint guard only scopes to `OPEN_STATUSES`,
   excluding resolved/closed/cancelled/rejected), and treats this as
   settled, existing, evidence-based policy, not an open question —
   included here only because the mission explicitly lists it as a
   possible PRODUCT_POLICY_BLOCKED item; this slice's position is that it
   is **not** blocked, it is already answered by the code.
3. **`complaints.admin_router`'s own boundary** — re-confirmed but not
   independently re-audited this slice (out of scope).
4. **Future complaint-specific permissions / future customer refund
   policy (e.g. cash refunds)** — not addressed, per explicit
   out-of-scope instruction.
