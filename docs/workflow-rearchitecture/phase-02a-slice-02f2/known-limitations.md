# Known Limitations — Slice 2F-2

1. **`create_member_login` remains an unimplemented stub** — returns no
   real credentials, creates no `users` row. Discovered, not fixed (new
   engineering behavior out of scope). See `product-decisions-required.md`
   item 1.
2. **No per-technician individual availability/schedule capability exists**
   — all availability configuration in this router is tenant-wide,
   `tenant_owner`-only. Confirmed, not built (see
   `availability-ownership-decision.md`, `product-decisions-required.md`
   item 2).
3. **`create_team_member` has no duplicate-invitation detection** — a
   data-quality gap, not a security gap (still correctly tenant-scoped and
   owner-gated). Not fixed this slice.
4. **`update_availability_exception`'s final read-back SELECT is
   technically still unscoped**, but structurally safe: the same function
   already performed a tenant-filtered existence check earlier and the
   `exception_id` cannot change mid-request, so no cross-tenant leak is
   possible through this specific code path — left as-is rather than
   changed defensively without a proven exploit, to keep the diff minimal
   and evidence-based.
5. **`set_area_coverage` (per-area coverage) was not re-verified this
   slice** — it already had `require_tenant_mutation_permission` from a
   prior (Slice 2F-1-era) change and was outside this slice's swap scope;
   its existing tests were not re-run individually, only as part of the
   broader partition (which passed).
6. **Provider status/onboarding "refresh" endpoints have limited
   observable behavior in tests** — `refresh_onboarding` is a pure no-op
   stub; `refresh_provider_status`'s real computation could only be proven
   to clear the auth layer (via the accepted TypeError-past-auth pattern),
   not asserted for correct business output, since the global
   `mock_database` fixture cannot support its real arithmetic.
7. **A full-repository test run was not completed** — 483 targeted + 269
   broader-partition tests (752 total, 0 failures) is the evidence base,
   not claimed as full-repository coverage.
8. **`readonly@demo-ac-services.local` remains untouched; migration 144
   remains unapplied; `tenant_engine.router` was not modified** — all
   confirmed per the brief's explicit exclusions.
9. **Pre-existing duplicate-operation-ID warnings** in
   `service_setup/templates_router.py` remain, unrelated, unfixed (same as
   every prior slice).
