# FINAL-L5-04 — Permission-Aware Menu Visibility / API Matrix

Live API checks this sprint (real accounts, real tokens) against 4 representative endpoints backing real nav items, covering 5 of the mission's 9 listed roles (Platform Super Admin, Tenant Owner, Tenant Read Only, Technician, Customer — Admin Operations/Admin Finance/Admin Read Only/Tenant Manager were not separately tested this sprint since no dedicated seeded accounts for those specific sub-roles were confirmed available; see Remaining Blockers).

| Endpoint (backs nav item) | super_admin | tenant_owner | tenant_readonly | technician | customer | anonymous |
|---|---|---|---|---|---|---|
| `GET /v1/admin/verticals` (Verticals menu) | 200 | 403 | 403 | 403 | 403 | 401 |
| `GET /v1/provider/my-records/jobs` (Jobs menu) | 200 | 200 | 200 | 200 | 200* | 401 |
| `GET /v1/customer/bookings` (Bookings menu) | 200 | 200* | 200* | 200* | 200 | 401 |
| `GET /v1/provider/usage-credits/balance` (Usage Credits menu) | 403 | 200 | 200 | 200 | 403 | 401 |

\* = soft-block pattern (200 with empty `items`, zero real data exposed) — the same, already-documented, carried finding from FINAL-L5-02B, not a new discovery. Re-verified this sprint to confirm it still holds after FINAL-L5-03's changes.

## Analysis against required checks
1. **Required permission is defined** — the admin-verticals endpoint correctly requires `require_super_admin`; confirmed via source read of `admin_router.py`.
2. **Allowed role sees item** — super_admin sees Verticals (200); tenant_owner/readonly/technician see Jobs and Usage Credits (200).
3. **Disallowed role does not see item** — tenant_owner/readonly/technician/customer all correctly rejected (403) from the admin-only Verticals endpoint; super_admin and customer correctly rejected (403) from the tenant-scoped Usage Credits endpoint (super_admin has no `tenant_id` to scope by, correctly rejected rather than silently allowed).
4. **Direct URL remains protected** — confirmed at the API layer for all 4 endpoints (this is the authoritative layer; frontend route guards are secondary per rule 3).
5. **Read-only role sees read routes but not mutation-only routes** — `tenant_readonly` gets 200 on all 3 read endpoints tested; mutation-endpoint rejection (403-before-422) was established and proven in FINAL-L5-01D and re-confirmed unaffected in FINAL-L5-02B/03 — not re-tested from scratch this sprint (no tenant-portal or backend auth code was touched this sprint that could regress it).
6. **Finance-only routes do not appear for operations-only users** — not independently testable this sprint (no dedicated "Admin Finance"/"Admin Operations" sub-role accounts were available to log in as — see Remaining Blockers).
7. **Configuration pages appear only to authorized roles** — confirmed for the Verticals configuration endpoint (super_admin only).

## Known, carried, honestly-repeated finding
The `200`-with-empty-body soft-block pattern on `/v1/provider/my-records/jobs` (for customer) and `/v1/customer/bookings` (for tenant/technician) means these endpoints do not literally return `403`/`404` for out-of-scope roles — they return a safe empty list. This was already documented as low-severity (no data exposure) in FINAL-L5-01D/02B and is not re-litigated as a new finding here, but is repeated because Part 10 explicitly asks for this exact matrix.

Machine-readable version: `permission-navigation-matrix.json`.

## Result
No unauthorized role received real data from any endpoint tested. The literal-status-code nuance (200-soft-block vs. 403) is carried, known, and non-blocking. No `NOT_READY_FINAL_L5_04_PERMISSION_VISIBILITY_FAILED` from this evidence — real data leakage was not found in any tested combination.
