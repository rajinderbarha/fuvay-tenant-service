# Known Limitations — Slice 2F-1A

1. **`confirm_termination`'s "90-day scheduled deletion" claim has no
   backing implementation** — a genuine, pre-existing gap discovered this
   slice, not fixed (new engineering behavior is out of scope for a
   policy-closure slice). See `sensitive-capability-policy.md` and
   `product-decisions-required.md` item 4.
2. **`request_gdpr_deletion` has no anonymization/deletion execution
   mechanism** — only writes an audit-log entry. A compliance-relevant gap,
   escalated in `product-decisions-required.md` item 5, not resolved here.
3. **2 genuine product decisions remain fully open** (voluntary tenant
   pause as a distinct feature; a true subscription-cancellation
   capability) — correctly classified `BLOCKED_PENDING_PRODUCT_DECISION`,
   not guessed at.
4. **The `tenant_engine.router` `/suspend` vs `admin_router.py`
   `/v1/admin/tenants/{id}/suspend` duplication was identified, not
   resolved** — both exist, both work, both require super_admin; a future
   slice could consolidate them, but doing so was out of this slice's scope
   ("do not remove without a safe compatibility plan").
5. **No code changed this slice** — this is a documentation/classification/
   test-completion slice by design; if the reader expected a functional
   change, there isn't one (the guard code from Slice 2F-1 was already
   correct and is unchanged).
6. **The 8 `PLATFORM_ADMIN_ONLY`-corrected endpoints' underlying permissions
   (`tenant:suspend`, `tenant:reinstate`, `tenant:terminate`,
   `tenant:plan:manage`, `tenant:data:delete`) are still, technically,
   defined but granted to no role** — this remains true after this slice;
   the correction only relabels the *policy intent*, it does not add a role
   grant (deliberately, per the brief's explicit prohibition on granting
   permissions to make anything pass).
7. **A full-repository test run was not completed** — 430 targeted + 364
   broader-partition tests (794 total, 0 failures) is the evidence base,
   not claimed as full-repository coverage.
8. **`readonly@demo-ac-services.local` remains unremediated and untouched**;
   migration 144 remains unapplied at revision 143. Neither was touched, per
   the brief's explicit exclusion.
9. **Pre-existing duplicate-operation-ID warnings** in
   `service_setup/templates_router.py` remain, unrelated, unfixed (same as
   every prior slice).
