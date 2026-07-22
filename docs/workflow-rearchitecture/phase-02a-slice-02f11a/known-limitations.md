# Known Limitations — Slice 2F-11A

1. **`real_estate_lead`'s own authorization pattern was documented, not
   evaluated or hardened** — out of scope (no capability overlap exists
   to require it).
2. **No frontend surface exists for any route in either module relevant
   to this slice's read fix** — reads (like the mutations before them)
   remain backend-only in terms of active UI callers.
3. **Business-wide staff/owner read access is not assignment-limited**
   (any tenant_owner/staff can read any lead's timeline/notes within
   their own tenant, not just their own assigned leads) — this is a
   deliberate, evidence-supported design choice (back-office visibility),
   not a defect, but is recorded here for completeness since it differs
   from the mutation guard's assignment-scoped behavior.
4. **`--verify-overlap` runtime tool check was not run this slice** (CLI
   usage required arguments not exercised) — route-overlap risk was
   instead confirmed via direct model/route inspection (no shared table,
   no shared route path between the two modules).
