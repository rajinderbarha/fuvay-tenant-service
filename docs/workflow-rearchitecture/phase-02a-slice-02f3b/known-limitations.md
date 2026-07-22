# Known Limitations — Slice 2F-3B

1. **`reassign_job`/`cancel_assignment`/`schedule_job`'s ownership
   mechanisms were not independently re-verified line-by-line this slice**
   — only the access-scope guard was added on top of their pre-existing
   (unmodified) logic. Flagged for a future dedicated audit if concerns
   arise.
2. **`provider_install_parts_request`'s exact provider-only enforcement
   mechanism was not re-traced end-to-end** — confirmed unchanged, not
   re-examined for correctness.
3. **Cross-tenant / wrong-record-type / repeated-transition scenarios for
   the 4 provider-assignment and 4 execution-parts endpoints were not
   individually re-exercised via HTTP this slice beyond guard-clearing
   proof** — their pre-existing mechanisms were read and confirmed
   unchanged, not independently re-verified end-to-end with a live-
   equivalent fixture.
4. **The 3 platform-admin endpoints' frontend caller, confirmation
   behavior, and audit behavior were not independently re-verified this
   slice** — assumed unchanged and super-admin-app-only, consistent with
   prior slices' pattern, not freshly confirmed.
5. **The dead `staff_accept_job`/`staff_reject_job` functions remain in
   the codebase** — preserved per the brief's explicit instruction not to
   delete without separate justification.
6. **`ERR_ACCESS_DENIED`'s error message is deliberately generic** ("Job
   not found.") to avoid leaking cross-tenant record existence — this
   means a legitimate "wrong tenant" error and a genuine "job doesn't
   exist" error are indistinguishable to the caller by design, which is
   the correct security tradeoff but slightly less helpful for legitimate
   debugging.
7. **A full-repository test run was not completed** — 877 combined tests
   (561 targeted + 316 broader partition), 0 failures, is the evidence
   base.
8. **`readonly@demo-ac-services.local` remains untouched; migration 144
   remains unapplied; `tenant_engine.router` and `provider_portal.router`
   were not modified** — all confirmed per the brief's explicit exclusions.
9. **Pre-existing duplicate-operation-ID warnings** in
   `service_setup/templates_router.py` and `admin_catalog/*` remain,
   unrelated, unfixed (same as every prior slice).
