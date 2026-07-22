# Known Limitations — Slice 2F-1

1. **8 of the 19 newly-guarded permissions are granted to no role today**
   (`tenant:suspend`, `tenant:reinstate`, `tenant:terminate`,
   `tenant:plan:manage`, `tenant:data:delete`) — only reachable via
   `super_admin`'s `P.ALL` wildcard. The access-scope guard this slice added
   has zero practical effect on these 8 right now (super_admin is exempt
   from that check). This is documented, not silently glossed over — see
   `tenant-engine-mutation-inventory.csv`'s `in_tenant_owner_bundle` column.
2. **This slice closes exactly 1 of the ~24 router modules** Slice 2F's
   platform-wide inventory identified. 18+ modules remain with 0
   access-scope-aware mutation guards. Slice 2F's `NOT_READY_MUTATION_GAPS`
   disposition is unchanged by this slice.
3. **Cross-tenant and owner-success HTTP proof was run against a
   representative sample (4 of 19 endpoints), not all 19** — the remaining
   15 share the identical guard code path (`require_tenant_mutation_permission`
   wraps `require_permission` and then checks `access_scope`) and the
   identical `_assert_own_tenant_or_super_admin` ownership call, so the
   representative sample is a reasonable proxy, but this is not the same
   as 19/19 direct HTTP proof for those two specific properties (read-only
   denial WAS proven directly for all 19).
4. **`/health` was excluded from the read-path regression sample** — it hits
   a pre-existing, unrelated mock-fidelity gap (`Decimal(str(MagicMock()))`
   crashes several layers past the auth gate, in `usage_credits.service`),
   the same class of gap `test_final_l5_01b_admin_tenant_rbac.py` already
   documents for pagination math. Not an auth regression, not fixed (out of
   scope), just excluded from this slice's specific read-path sample.
5. **The `deactivate_staff` Redis fix has the same fail-open Redis-failure
   characteristic** as `update_permissions`'s Slice 2F fix — a Redis outage
   at the exact moment of deactivation leaves only DB-side revocation in
   effect until natural token expiry.
6. **A full-repository test run was not completed** (same limitation as
   every prior slice) — 382 targeted tests is the evidence base.
7. **`readonly@demo-ac-services.local` remains unremediated and untouched**,
   per the brief's explicit exclusion. Migration 144 remains unapplied at
   revision 143.
8. **Pre-existing duplicate-operation-ID warnings** in
   `service_setup/templates_router.py` remain, unrelated, unfixed (same as
   every prior slice).
