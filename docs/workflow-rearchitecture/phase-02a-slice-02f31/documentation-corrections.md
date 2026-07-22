# Documentation Corrections - Slice 2F-31

1. **Canonical guard_status for the 6 closed routes** was initially recorded
   as `TENANT_MUTATION_ROLE_SCOPE_AWARE`; the live classifier
   (`authority_model_2f26e.py`) resolves `require_staff_or_above_mutation` to
   `STAFF_EXECUTION_ROLE_SCOPE_AWARE` (both are in the VERIFIED/protected set,
   so coverage arithmetic is unaffected). Corrected to match the classifier
   that the recount tests actually run, plus the historical 2F-21/2F-23
   runtime-reverification snapshots that record live state.
2. **2F-27A/28/29/30 point-in-time artifacts were not rewritten.** Their own
   CSVs are untouched; only the CURRENT executable test assertions that
   compared them to the live canonical file were reframed with explicit
   reconciliation formulas (closed routes removed, added routes included).
3. No prior numeric coverage claim before this slice is corrected.
