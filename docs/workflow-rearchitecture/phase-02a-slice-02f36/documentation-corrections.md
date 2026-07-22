# Documentation Corrections

While rebaselining historical tests for the live canonical CSV move
(273/252/21 → 297/294/3), discovered and corrected one prior slice's
route-adjudication error made during THIS slice's own initial
implementation pass (not a pre-existing defect from an earlier slice):

1. `POST /v1/bookings` was initially added as a new canonical row with
   disposition `TENANT_PROVIDER_MUTATION_ADD`. Cross-checking against
   the pre-existing `app.engines.booking.router` matrix documentation
   (established Slice 2F-15C) showed `create_booking` is explicitly
   `CUSTOMER_SELF_SERVICE_MUTATION` — reachable by the customer persona,
   and therefore correctly excluded from the tenant-only canonical CSV
   under the program's Design A convention. The erroneous canonical row
   was removed before any test file was written against it, and the
   route was re-adjudicated as `CUSTOMER_SELF_SERVICE_EXCLUDE` (already
   protected, no code change needed) in `held-route-adjudication.csv`.
   This was caught and corrected within this same slice, before it ever
   reached a committed or tested state — no downstream artifact carries
   the incorrect classification.

2. 9 historical test files (2F-14A, 2F-17A, 2F-19, 2F-25, 2F-25A, 2F-26,
   2F-26B, 2F-26C, 2F-26D) asserted the live canonical CSV's total/
   protected/unprotected counts inline rather than against a frozen
   snapshot; each was individually updated at its exact assertion line
   (never a blanket find/replace) to the new 297/294/3 figures, with a
   one-line comment attributing the change to this slice. No frozen
   point-in-time slice artifact was rewritten.
