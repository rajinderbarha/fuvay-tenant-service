# Known Limitations — Slice 2F-23

1. **A confirmed cross-tenant vulnerability is being left open for one more
   slice.** `flag_review` lets any authenticated principal set any review in
   any tenant to `flagged`. This slice is discovery-only and explicitly
   prohibited from implementing, so the defect is documented and scheduled
   for 2F-24 rather than fixed. That is the correct scope discipline, but the
   exposure is real and live in the meantime, so it is stated plainly rather
   than buried in a risk table.

2. **The 19 rows were verified statically, not exercised.** Mounting,
   dependency chains, service logic and ownership checks were confirmed by
   runtime route introspection and direct source reading. No route was
   invoked against a live database or HTTP server — none is available in this
   environment. The cross-tenant finding is therefore proven by code
   inspection (an unfiltered `SELECT ... WHERE id = :id` followed by a status
   write), not by an executed exploit.

3. **Read-privacy of the remaining routes was not fully audited.** Reads were
   inventoried and their dependencies noted, but this slice examined mutation
   surfaces. `provider_run_report`'s export/download privacy in particular is
   flagged `READ_PRIVACY_UNVERIFIED` rather than cleared.

4. **Frontend/mobile callers were not audited for the remaining 19.** The
   inventory records callers only where immediately discoverable, as the
   mission allows. A full caller audit belongs to each implementation slice.

5. **Analytics `filters` handling not traced to its terminus.** `filters` is
   a client-controlled dict passed into `run_report`. `tenant_id` is passed
   separately and `SCOPE_PROVIDER` is hardcoded, but whether a crafted filter
   can widen the query was not traced through the report service. Recorded as
   a risk to resolve when that module is implemented, not as a cleared item.

6. **`mutation-enforcement-matrix.csv` remains stale**, consistent with the
   convention held since 2F-19. The row-level inventory is authoritative.

7. **Guard-status vocabulary differs between the canonical CSV and the
   runtime tool** for 13 rows (`ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE` vs
   `PERMISSION_ONLY_NOT_SCOPE_AWARE`). Both mean unprotected and coverage is
   unaffected; not rewritten, because difference is not evidence of error.

8. **Two stale Slice-2D canary tests remain failing** and were deliberately
   not touched, per this slice's explicit prohibition. They still require the
   `tenant-readonly-decision.md` conclusion to be revisited.

9. **No full-application sweep for net-new routes** was performed. This slice
   reconciles the known 19-row queue; the last exhaustive sweep was 2F-17A.
   If routes were added since, they would not appear here — stated rather
   than assumed away.
